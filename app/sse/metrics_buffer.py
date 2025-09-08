import time
import logging
from collections import deque
from typing import Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class SmartMetricsBuffer:
    """
    실시간 메트릭을 위한 스마트 예측 버퍼
    
    Features:
    - 전진 보간법 (Forward Interpolation): 이전 두 값의 기울기로 예측
    - 지수 평활법 (Exponential Smoothing): 최근 값에 높은 가중치 부여
    - 연속 예측 제한: 최대 6회(30초) 후 fallback
    - 오차 누적 방지: 실제값 복구시 소급 보정
    - 백분율 메트릭 지원: 0-100% 범위 제한
    """
    
    def __init__(self, metric_name: str = "metric", metric_type: str = "percentage", 
                 max_value: float = 100.0, window_size: int = 10, max_prediction_streak: int = 6):
        """
        Args:
            metric_name: 메트릭 이름 (로깅용)
            metric_type: 메트릭 타입 ('percentage' 또는 'absolute')
            max_value: 최대값 (백분율은 100.0)
            window_size: 버퍼 크기 (기본 10개 = 50초 히스토리)
            max_prediction_streak: 최대 연속 예측 횟수
        """
        self.metric_name = metric_name
        self.metric_type = metric_type
        self.max_value = max_value
        self.max_prediction_streak = max_prediction_streak
        
        # 데이터 버퍼들 (FIFO)
        self.values = deque(maxlen=window_size)
        self.timestamps = deque(maxlen=window_size)
        self.is_predicted = deque(maxlen=window_size)
        self.confidence = deque(maxlen=window_size)
        
        # 연속 예측 상태 추적
        self.prediction_streak = 0
        
        # 지수 평활 상수 (0.1 = 안정, 0.9 = 민감)
        self.alpha = 0.3
        
        logger.info(f"SmartMetricsBuffer initialized for {metric_name} "
                   f"(type={metric_type}, max_value={max_value})")
    
    def add_value(self, value: float, predicted: bool = False, timestamp: Optional[datetime] = None) -> None:
        """
        새로운 값을 버퍼에 추가
        
        Args:
            value: 메트릭 값
            predicted: 예측값 여부
            timestamp: 타임스탬프 (None이면 현재 시간 사용)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # 값 범위 제한
        if self.metric_type == "percentage":
            value = min(self.max_value, max(0.0, value))
        else:
            value = max(0.0, value)  # 음수만 방지
        
        # 신뢰도 계산
        if predicted:
            self.prediction_streak += 1
            confidence = max(0.2, 1.0 - self.prediction_streak * 0.15)
        else:
            self.prediction_streak = 0  # 실제값 복구시 리셋
            confidence = 1.0
        
        # 버퍼에 추가
        self.values.append(value)
        self.timestamps.append(timestamp)
        self.is_predicted.append(predicted)
        self.confidence.append(confidence)
        
        logger.debug(f"{self.metric_name}: Added {'predicted' if predicted else 'actual'} "
                    f"value {value:.2f} (confidence={confidence:.2f}, streak={self.prediction_streak})")
        
        # 실제값 복구시 이전 예측값들 보정
        if not predicted and self.prediction_streak > 1:
            self._correct_previous_predictions(value)
    
    def predict_next(self) -> Optional[float]:
        """
        다음 값을 예측
        
        Returns:
            float: 예측값 (예측 불가시 None)
        """
        if len(self.values) == 0:
            logger.warning(f"{self.metric_name}: No values in buffer for prediction")
            return None
        
        # 연속 예측 제한 체크
        if self.prediction_streak >= self.max_prediction_streak:
            logger.info(f"{self.metric_name}: Max prediction streak reached ({self.max_prediction_streak}), "
                       "using exponential decay")
            return self._exponential_decay_fallback()
        
        # 단일 값만 있는 경우
        if len(self.values) == 1:
            return float(self.values[-1])
        
        # 전진 보간법 + 지수 평활법
        prediction = self._forward_interpolation()
        
        # 범위 제한
        if self.metric_type == "percentage":
            prediction = min(self.max_value, max(0.0, prediction))
        else:
            prediction = max(0.0, prediction)
        
        return prediction
    
    def _forward_interpolation(self) -> float:
        """
        전진 보간법으로 다음 값 예측
        
        Returns:
            float: 예측값
        """
        # 가중 평균 기울기 계산
        slope = self._calculate_weighted_slope()
        
        # 기준값 (최근 값 또는 지수 평활값)
        base_value = self._get_smoothed_base_value()
        
        # 5초 후 예측값
        predicted_value = base_value + slope * 5
        
        logger.debug(f"{self.metric_name}: Forward interpolation - base={base_value:.2f}, "
                    f"slope={slope:.4f}/s, prediction={predicted_value:.2f}")
        
        return predicted_value
    
    def _calculate_weighted_slope(self) -> float:
        """
        신뢰도 가중 평균으로 기울기 계산
        
        Returns:
            float: 기울기 (단위/초)
        """
        if len(self.values) < 2:
            return 0.0
        
        # 최근 3개 값 사용 (가용한 만큼)
        use_count = min(3, len(self.values))
        recent_values = list(self.values)[-use_count:]
        recent_confidence = list(self.confidence)[-use_count:]
        recent_timestamps = list(self.timestamps)[-use_count:]
        
        slopes = []
        weights = []
        
        for i in range(1, len(recent_values)):
            # 시간 차이 계산 (초 단위)
            time_diff = (recent_timestamps[i] - recent_timestamps[i-1]).total_seconds()
            if time_diff <= 0:
                time_diff = 5.0  # 기본 5초 간격 가정
            
            # 기울기 계산
            slope = (recent_values[i] - recent_values[i-1]) / time_diff
            
            # 가중치 (두 점의 신뢰도 곱)
            weight = recent_confidence[i] * recent_confidence[i-1]
            
            slopes.append(slope)
            weights.append(weight)
        
        # 가중 평균 기울기
        if sum(weights) > 0:
            weighted_slope = sum(s * w for s, w in zip(slopes, weights)) / sum(weights)
        else:
            weighted_slope = 0.0
        
        return weighted_slope
    
    def _get_smoothed_base_value(self) -> float:
        """
        지수 평활법으로 기준값 계산
        
        Returns:
            float: 평활된 기준값
        """
        if len(self.values) == 1:
            return float(self.values[-1])
        
        # 최근 두 값에 지수 평활법 적용
        current_value = self.values[-1]
        previous_value = self.values[-2]
        
        # 신뢰도에 따라 평활 상수 조정
        current_confidence = self.confidence[-1]
        adjusted_alpha = self.alpha * current_confidence
        
        smoothed = adjusted_alpha * current_value + (1 - adjusted_alpha) * previous_value
        
        logger.debug(f"{self.metric_name}: Exponential smoothing - "
                    f"current={current_value:.2f}, previous={previous_value:.2f}, "
                    f"alpha={adjusted_alpha:.3f}, smoothed={smoothed:.2f}")
        
        return smoothed
    
    def _exponential_decay_fallback(self) -> float:
        """
        연속 예측 한계 도달시 지수적 감소 적용
        
        Returns:
            float: 감소된 값
        """
        if len(self.values) == 0:
            return 0.0
        
        # 마지막 실제값 찾기
        last_actual_value = None
        for i in range(len(self.is_predicted)):
            if not self.is_predicted[-(i+1)]:
                last_actual_value = self.values[-(i+1)]
                break
        
        if last_actual_value is None:
            last_actual_value = self.values[0]
        
        # 지수적 감소 (매 5초마다 5% 감소)
        decay_factor = 0.95 ** (self.prediction_streak - self.max_prediction_streak + 1)
        decayed_value = last_actual_value * decay_factor
        
        logger.info(f"{self.metric_name}: Exponential decay fallback - "
                   f"last_actual={last_actual_value:.2f}, factor={decay_factor:.3f}, "
                   f"result={decayed_value:.2f}")
        
        return decayed_value
    
    def _correct_previous_predictions(self, actual_value: float) -> None:
        """
        실제값 복구시 이전 예측값들을 소급 보정
        
        Args:
            actual_value: 복구된 실제값
        """
        if len(self.values) < 2:
            return
        
        last_predicted = self.values[-2]  # 마지막 예측값
        prediction_error = actual_value - last_predicted
        
        # 이전 예측값들을 점진적으로 보정
        correction_count = 0
        for i in range(len(self.is_predicted)):
            if self.is_predicted[-(i+1)]:  # 예측값이면
                # 거리에 따라 보정 강도 감소
                correction_factor = (0.5 ** i) * 0.3  # 최대 30% 보정
                correction = prediction_error * correction_factor
                
                old_value = self.values[-(i+1)]
                new_value = old_value + correction
                
                # 범위 제한 적용
                if self.metric_type == "percentage":
                    new_value = min(self.max_value, max(0.0, new_value))
                else:
                    new_value = max(0.0, new_value)
                
                self.values[-(i+1)] = new_value
                correction_count += 1
                
                logger.debug(f"{self.metric_name}: Corrected prediction[{i}] "
                            f"{old_value:.2f} -> {new_value:.2f} (correction={correction:.2f})")
            else:
                break  # 실제값에 도달하면 중단
        
        if correction_count > 0:
            logger.info(f"{self.metric_name}: Corrected {correction_count} previous predictions "
                       f"based on actual value {actual_value:.2f} (error={prediction_error:.2f})")
    
    def get_current_state(self) -> dict:
        """
        현재 버퍼 상태 반환 (디버깅/모니터링용)
        
        Returns:
            dict: 버퍼 상태 정보
        """
        if len(self.values) == 0:
            return {
                'metric_name': self.metric_name,
                'current_value': None,
                'prediction_streak': self.prediction_streak,
                'confidence': 0.0,
                'buffer_size': 0
            }
        
        return {
            'metric_name': self.metric_name,
            'current_value': float(self.values[-1]),
            'is_predicted': self.is_predicted[-1] if self.is_predicted else False,
            'prediction_streak': self.prediction_streak,
            'confidence': float(self.confidence[-1]) if self.confidence else 0.0,
            'buffer_size': len(self.values),
            'metric_type': self.metric_type,
            'max_value': self.max_value
        }