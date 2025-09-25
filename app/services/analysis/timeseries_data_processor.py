"""
시계열 데이터 전처리 및 노이즈 제거 모듈

부하테스트 시계열 데이터에서 노이즈를 제거하고
AI 분석에 적합한 형태로 전처리합니다.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from statistics import mean, stdev

logger = logging.getLogger(__name__)


class TimeseriesDataProcessor:
    """시계열 데이터 전처리 클래스"""

    def __init__(self):
        # 노이즈 제거 기준 설정
        self.startup_trim_percentage = 0.1  # 초기 10% 제거
        self.shutdown_trim_percentage = 0.05  # 종료 5% 제거
        self.outlier_threshold = 2.5  # 표준편차 기준 이상치 제거 임계값

    def process_k6_timeseries(
        self,
        timeseries_data: List[Dict[str, Any]],
        remove_noise: bool = False
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        k6 시계열 데이터 전처리

        Args:
            timeseries_data: k6 시계열 데이터 리스트
            remove_noise: 노이즈 제거 여부

        Returns:
            (전처리된 데이터, 분석용 컨텍스트 문자열) 튜플
        """
        if not timeseries_data:
            return [], "시계열 데이터가 없습니다."

        try:
            # 전체 데이터와 시나리오별 데이터 분리
            overall_data = [d for d in timeseries_data if d.get('scenario_name') is None]
            scenario_data = [d for d in timeseries_data if d.get('scenario_name') is not None]

            logger.info(f"Processing k6 timeseries: {len(overall_data)} overall points, {len(scenario_data)} scenario points")

            # 노이즈 제거 적용
            if remove_noise and overall_data:
                overall_data = self._remove_noise_from_timeseries(overall_data)
                scenario_data = self._remove_noise_from_timeseries(scenario_data) if scenario_data else []

            # 분석용 컨텍스트 생성
            context = self._generate_k6_analysis_context(overall_data, scenario_data)

            # 전처리된 데이터 결합
            processed_data = overall_data + scenario_data

            logger.info(f"Processed k6 timeseries: {len(processed_data)} points after noise removal")

            return processed_data, context

        except Exception as e:
            logger.error(f"Error processing k6 timeseries data: {e}")
            return timeseries_data, "시계열 데이터 처리 중 오류가 발생했습니다."

    def process_resource_timeseries(
        self,
        resource_usage_data: List[Dict[str, Any]],
        remove_noise: bool = False
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        리소스 사용량 시계열 데이터 전처리

        Args:
            resource_usage_data: 리소스 사용량 데이터 리스트
            remove_noise: 노이즈 제거 여부

        Returns:
            (전처리된 데이터, 분석용 컨텍스트 문자열) 튜플
        """
        if not resource_usage_data:
            return [], "리소스 사용량 데이터가 없습니다."

        try:
            processed_resources = []

            for resource in resource_usage_data:
                pod_name = resource.get('pod_name', 'unknown')
                service_type = resource.get('service_type', 'unknown')
                resource_data = resource.get('resource_data', [])

                if not resource_data:
                    continue

                # 노이즈 제거 적용
                if remove_noise:
                    resource_data = self._remove_noise_from_resource_data(resource_data)

                processed_resource = {
                    'pod_name': pod_name,
                    'service_type': service_type,
                    'resource_data': resource_data
                }

                processed_resources.append(processed_resource)

            # 분석용 컨텍스트 생성
            context = self._generate_resource_analysis_context(processed_resources)

            logger.info(f"Processed resource timeseries: {len(processed_resources)} pods")

            return processed_resources, context

        except Exception as e:
            logger.error(f"Error processing resource timeseries data: {e}")
            return resource_usage_data, "리소스 시계열 데이터 처리 중 오류가 발생했습니다."

    def _remove_noise_from_timeseries(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """시계열 데이터에서 노이즈 제거"""

        if len(data) < 10:  # 데이터가 너무 적으면 노이즈 제거 안함
            return data

        # 시간순 정렬
        sorted_data = sorted(data, key=lambda x: x['timestamp'])

        # 초기/종료 구간 제거
        total_points = len(sorted_data)
        start_trim = int(total_points * self.startup_trim_percentage)
        end_trim = int(total_points * self.shutdown_trim_percentage)

        if start_trim + end_trim >= total_points:
            # 너무 많이 제거하게 되면 중간 50% 구간만 사용
            start_idx = int(total_points * 0.25)
            end_idx = int(total_points * 0.75)
            trimmed_data = sorted_data[start_idx:end_idx]
        else:
            end_idx = total_points - end_trim if end_trim > 0 else total_points
            trimmed_data = sorted_data[start_trim:end_idx]

        # 이상치 제거 (TPS 기준)
        cleaned_data = self._remove_outliers(trimmed_data, 'tps')

        logger.debug(f"Noise removal: {total_points} -> {len(trimmed_data)} -> {len(cleaned_data)} points")

        return cleaned_data

    def _remove_noise_from_resource_data(self, resource_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """리소스 데이터에서 노이즈 제거"""

        if len(resource_data) < 10:
            return resource_data

        # 시간순 정렬
        sorted_data = sorted(resource_data, key=lambda x: x['timestamp'])

        # 초기/종료 구간 제거
        total_points = len(sorted_data)
        start_trim = int(total_points * self.startup_trim_percentage)
        end_trim = int(total_points * self.shutdown_trim_percentage)

        if start_trim + end_trim >= total_points:
            start_idx = int(total_points * 0.25)
            end_idx = int(total_points * 0.75)
            trimmed_data = sorted_data[start_idx:end_idx]
        else:
            end_idx = total_points - end_trim if end_trim > 0 else total_points
            trimmed_data = sorted_data[start_trim:end_idx]

        logger.debug(f"Resource noise removal: {total_points} -> {len(trimmed_data)} points")

        return trimmed_data

    def _remove_outliers(self, data: List[Dict[str, Any]], metric_key: str) -> List[Dict[str, Any]]:
        """이상치 제거 (표준편차 기준)"""

        if len(data) < 5:
            return data

        try:
            values = [d.get(metric_key, 0) for d in data if d.get(metric_key) is not None]

            if len(values) < 5:
                return data

            mean_val = mean(values)
            std_val = stdev(values)

            if std_val == 0:  # 표준편차가 0이면 모든 값이 같음
                return data

            # 표준편차 기준 이상치 제거
            filtered_data = []
            for d in data:
                value = d.get(metric_key, 0)
                if value is not None:
                    z_score = abs(value - mean_val) / std_val
                    if z_score <= self.outlier_threshold:
                        filtered_data.append(d)

            return filtered_data if filtered_data else data

        except Exception as e:
            logger.warning(f"Error removing outliers: {e}")
            return data

    def _generate_k6_analysis_context(
        self,
        overall_data: List[Dict[str, Any]],
        scenario_data: List[Dict[str, Any]]
    ) -> str:
        """k6 데이터 분석용 컨텍스트 생성"""

        context_parts = []

        if overall_data:
            # 전체 성능 패턴 분석
            tps_values = [d.get('tps', 0) for d in overall_data if d.get('tps') is not None]
            response_times = [d.get('avg_response_time', 0) for d in overall_data if d.get('avg_response_time') is not None]
            error_rates = [d.get('error_rate', 0) for d in overall_data if d.get('error_rate') is not None]
            vus_values = [d.get('vus', 0) for d in overall_data if d.get('vus') is not None]

            context_parts.append("**k6 성능 시계열 패턴 분석**:")

            if tps_values:
                tps_trend = self._analyze_trend(tps_values)
                context_parts.append(f"- TPS 변화 패턴: {tps_trend} (최소 {min(tps_values):.1f} → 최대 {max(tps_values):.1f})")

            if response_times:
                rt_trend = self._analyze_trend(response_times)
                context_parts.append(f"- 응답시간 변화 패턴: {rt_trend} (최소 {min(response_times):.1f}ms → 최대 {max(response_times):.1f}ms)")

            if error_rates:
                error_trend = self._analyze_trend(error_rates)
                context_parts.append(f"- 에러율 변화 패턴: {error_trend} (최소 {min(error_rates):.2f}% → 최대 {max(error_rates):.2f}%)")

            if vus_values:
                vus_trend = self._analyze_trend(vus_values)
                vus_pattern_info = self._analyze_vus_pattern(vus_values)
                context_parts.append(f"- 가상 사용자 변화: {vus_trend} (최소 {min(vus_values)} → 최대 {max(vus_values)})")
                context_parts.append(f"  * VU 패턴 분석: {vus_pattern_info}")

                # VU 패턴 정보를 로그로 출력
                logger.info(f"VU Pattern Analysis - Trend: {vus_trend}, Pattern: {vus_pattern_info}, Range: {min(vus_values)}-{max(vus_values)}")

                # TPS-VU 상관관계 분석 (점진적 증가 패턴인 경우)
                if "ramping-vus" in vus_pattern_info or "점진적 증가" in vus_pattern_info:
                    correlation_analysis = self._analyze_tps_vu_correlation(overall_data)
                    if correlation_analysis["correlation"] != "insufficient_data":
                        context_parts.append(f"  * TPS-VU 상관관계: {correlation_analysis['pattern']} (상관계수 {correlation_analysis['coefficient']})")
                        logger.info(f"TPS-VU Correlation Analysis: {correlation_analysis}")

            context_parts.append(f"- 안정 구간 데이터 포인트: {len(overall_data)}개 (노이즈 제거 후)")

        # 시나리오별 데이터가 있는 경우
        if scenario_data:
            scenarios = set(d.get('scenario_name') for d in scenario_data if d.get('scenario_name'))
            context_parts.append(f"- 시나리오별 분석 가능: {len(scenarios)}개 시나리오")

        context_parts.append("")

        return "\n".join(context_parts)

    def _generate_resource_analysis_context(self, processed_resources: List[Dict[str, Any]]) -> str:
        """리소스 데이터 분석용 컨텍스트 생성"""

        context_parts = []

        if processed_resources:
            context_parts.append("**리소스 사용량 시계열 패턴 분석**:")

            for resource in processed_resources:
                pod_name = resource['pod_name']
                service_type = resource['service_type']
                resource_data = resource['resource_data']

                if not resource_data:
                    continue

                # CPU/Memory 사용 패턴 분석
                cpu_percentages = [d['usage']['cpu_percent'] for d in resource_data if 'usage' in d]
                memory_percentages = [d['usage']['memory_percent'] for d in resource_data if 'usage' in d]

                context_parts.append(f"- {pod_name} ({service_type}):")

                if cpu_percentages:
                    cpu_trend = self._analyze_trend(cpu_percentages)
                    context_parts.append(f"  * CPU 사용 패턴: {cpu_trend} (범위: {min(cpu_percentages):.1f}% - {max(cpu_percentages):.1f}%)")

                if memory_percentages:
                    memory_trend = self._analyze_trend(memory_percentages)
                    context_parts.append(f"  * Memory 사용 패턴: {memory_trend} (범위: {min(memory_percentages):.1f}% - {max(memory_percentages):.1f}%)")

                context_parts.append(f"  * 측정 포인트: {len(resource_data)}개 (노이즈 제거 후)")

        context_parts.append("")

        return "\n".join(context_parts)

    def _analyze_trend(self, values: List[float]) -> str:
        """수치 리스트의 변화 추세 분석"""

        if len(values) < 3:
            return "안정적"

        # 시간에 따른 변화율 계산
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]

        first_avg = mean(first_half)
        second_avg = mean(second_half)

        if first_avg == 0:
            return "증가" if second_avg > first_avg else "안정적"

        change_rate = ((second_avg - first_avg) / first_avg) * 100

        if change_rate > 10:
            return "증가 추세"
        elif change_rate < -10:
            return "감소 추세"
        else:
            return "안정적"

    def _analyze_vus_pattern(self, vus_values: List[float]) -> str:
        """VU 패턴 분석 - executor 유형과 부하 패턴 추론"""

        if len(vus_values) < 5:
            return "데이터 부족"

        # 패턴 분석을 위한 기본 통계
        min_vu = min(vus_values)
        max_vu = max(vus_values)
        avg_vu = mean(vus_values)

        # VU 변화량 계산
        vu_range = max_vu - min_vu
        vu_variance = max_vu / min_vu if min_vu > 0 else float('inf')

        # 점진적 변화 패턴 감지
        ramping_points = 0
        stable_points = 0

        for i in range(1, len(vus_values)):
            diff = abs(vus_values[i] - vus_values[i-1])
            if diff <= 1:  # VU 차이가 1 이하면 안정적
                stable_points += 1
            elif diff > 1:  # VU 차이가 1 초과면 변화
                ramping_points += 1

        # 패턴 판정
        if vu_range <= 5:  # VU 변화가 5 이하
            return f"constant-vus 패턴 (안정적, VU={int(avg_vu)})"

        elif ramping_points > stable_points:  # 변화가 더 많음
            if vu_variance > 2:  # VU가 2배 이상 변화
                # 단계적 변화 패턴 확인
                stages = self._detect_vu_stages(vus_values)
                if stages > 1:
                    return f"ramping-vus 패턴 ({stages}단계, {int(min_vu)}→{int(max_vu)} VU)"
                else:
                    return f"점진적 증가 패턴 ({int(min_vu)}→{int(max_vu)} VU)"
            else:
                return f"미세 조정 패턴 (범위: {int(min_vu)}-{int(max_vu)} VU)"

        else:  # 안정적인 구간이 더 많음
            return f"준안정 패턴 (평균 VU={int(avg_vu)}, 변동범위 {int(vu_range)})"

    def _detect_vu_stages(self, vus_values: List[float]) -> int:
        """VU 값에서 단계(stage) 개수 감지"""

        if len(vus_values) < 10:
            return 1

        # 연속적으로 같은 VU 값이 유지되는 구간 찾기
        stages = 1
        current_stage_vu = vus_values[0]
        same_vu_count = 1

        for i in range(1, len(vus_values)):
            if abs(vus_values[i] - current_stage_vu) <= 2:  # 허용 오차 2
                same_vu_count += 1
            else:
                # 새로운 단계 시작 (최소 5개 포인트 이상 유지되어야 함)
                if same_vu_count >= 5:
                    stages += 1
                current_stage_vu = vus_values[i]
                same_vu_count = 1

        return min(stages, 5)  # 최대 5단계까지만

    def _analyze_tps_vu_correlation(self, overall_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """TPS와 VU의 상관관계 분석"""

        if len(overall_data) < 10:
            return {"correlation": "insufficient_data", "coefficient": 0.0, "pattern": "unknown"}

        # VU와 TPS 데이터 추출
        valid_pairs = []
        for point in overall_data:
            vu = point.get('vus', 0)
            tps = point.get('tps', 0)
            if vu > 0 and tps > 0:
                valid_pairs.append((vu, tps))

        if len(valid_pairs) < 5:
            return {"correlation": "insufficient_data", "coefficient": 0.0, "pattern": "unknown"}

        # 피어슨 상관계수 계산
        import numpy as np
        try:
            vus = [pair[0] for pair in valid_pairs]
            tps_values = [pair[1] for pair in valid_pairs]

            correlation_coefficient = np.corrcoef(vus, tps_values)[0, 1]

            # 상관관계 패턴 분석
            if correlation_coefficient >= 0.8:
                correlation_type = "strong_positive"
                pattern = "linear_scaling"  # TPS가 VU를 잘 따라감
            elif correlation_coefficient >= 0.6:
                correlation_type = "moderate_positive"
                pattern = "moderate_scaling"  # TPS가 VU를 어느정도 따라감
            elif correlation_coefficient >= 0.3:
                correlation_type = "weak_positive"
                pattern = "poor_scaling"  # TPS가 VU를 잘 따라가지 못함
            else:
                correlation_type = "no_correlation"
                pattern = "bottlenecked"  # 명백한 병목 존재

            # 선형성 분석 (VU 대비 TPS 기울기)
            vu_range = max(vus) - min(vus)
            tps_range = max(tps_values) - min(tps_values)

            if vu_range > 0:
                scaling_ratio = tps_range / vu_range
            else:
                scaling_ratio = 0.0

            return {
                "correlation": correlation_type,
                "coefficient": round(correlation_coefficient, 3),
                "pattern": pattern,
                "scaling_ratio": round(scaling_ratio, 2),
                "vu_range": f"{min(vus)}-{max(vus)}",
                "tps_range": f"{min(tps_values):.1f}-{max(tps_values):.1f}"
            }

        except Exception as e:
            logger.error(f"Error calculating TPS-VU correlation: {e}")
            return {"correlation": "calculation_error", "coefficient": 0.0, "pattern": "unknown"}


def get_timeseries_data_processor() -> TimeseriesDataProcessor:
    """TimeseriesDataProcessor 인스턴스 반환 (싱글톤)"""

    if not hasattr(get_timeseries_data_processor, "_instance"):
        get_timeseries_data_processor._instance = TimeseriesDataProcessor()

    return get_timeseries_data_processor._instance