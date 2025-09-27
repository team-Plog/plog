
"""
부하테스트 성능 병목 탐지기

이 모듈은 k6 부하테스트 시계열 데이터를 분석하여 다음과 같은 성능 문제를 탐지합니다:
1. VUS 증가 시 응답시간 급증 (시스템 한계점)
2. CPU/메모리 과부하로 인한 병목
3. 에러율 급증 패턴
4. OOM Kill 등 리소스 고갈 현상

주요 특징:
- 단발성이 아닌 지속적 패턴만 탐지
- 다차원 상관관계 분석 (성능 + 리소스)
- AI 프롬프트에 직접 활용 가능한 분석 결과 생성
"""

from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics
import logging

logger = logging.getLogger(__name__)


class PerformanceProblemType(Enum):
    """성능 문제 유형"""
    RESPONSE_TIME_SPIKE = "response_time_spike"           # 응답시간 급증
    VUS_TPS_MISMATCH = "vus_tps_mismatch"                # VUS 증가하지만 TPS 정체
    CPU_OVERLOAD = "cpu_overload"                        # CPU 과부하
    MEMORY_EXHAUSTION = "memory_exhaustion"              # 메모리 고갈
    ERROR_RATE_SURGE = "error_rate_surge"               # 에러율 급증
    OUT_OF_MEMORY_KILL = "out_of_memory_kill"           # OOM Kill 발생


@dataclass
class PerformanceProblem:
    """탐지된 성능 문제 정보"""
    # 기본 정보
    problem_type: PerformanceProblemType
    severity_level: str  # "normal", "warning", "critical"
    confidence_score: float  # 0.0 ~ 1.0

    # 시간 정보
    started_at: datetime
    ended_at: datetime
    duration_seconds: float

    # 분석 정보
    root_cause_description: str  # 근본 원인 설명
    detected_evidence: List[str]  # 탐지 근거들
    performance_impact: str  # 성능에 미치는 영향

    # AI 분석용 컨텍스트
    ai_prompt_context: str  # AI에게 전달할 상황 설명

    # 상세 메트릭 데이터
    metric_details: Dict[str, Any]


class PerformanceBottleneckDetector:
    """
    부하테스트 성능 병목 탐지기

    이 클래스는 k6에서 수집된 시계열 데이터를 분석하여
    성능 병목과 이상 패턴을 자동으로 탐지합니다.
    """

    def __init__(self):
        """탐지기 초기화 - 각종 임계값 설정"""

        # 응답시간 급증 탐지 설정: 사용자 경험 중심
        self.RESPONSE_TIME_INCREASE_THRESHOLD_PERCENT = 200  # 응답시간 200% 이상 증가
        self.RESPONSE_TIME_USER_NOTICEABLE_MS = 100          # 사용자가 체감하는 최소 응답시간
        self.RESPONSE_TIME_SPIKE_MIN_DURATION_SEC = 15       # 최소 15초 지속

        # VUS-TPS 불일치 탐지 설정
        self.VUS_INCREASE_THRESHOLD_PERCENT = 30   # VUS 30% 이상 증가
        self.TPS_STAGNATION_THRESHOLD_PERCENT = 10 # TPS 10% 미만 증가

        # 리소스 과부하 탐지 설정
        self.HIGH_CPU_USAGE_THRESHOLD_PERCENT = 80    # CPU 80% 이상
        self.HIGH_MEMORY_USAGE_THRESHOLD_PERCENT = 85 # 메모리 85% 이상

        # 에러율 급증 탐지 설정
        self.ERROR_RATE_SPIKE_THRESHOLD_PERCENT = 5   # 에러율 5% 이상

        # 메모리 급락 탐지 설정 (OOM Kill)
        self.MEMORY_DROP_THRESHOLD_PERCENT = 30       # 메모리 30% 이상 급락

        # 패턴 지속성 확인 설정
        self.MINIMUM_PATTERN_DURATION_SEC = 20        # 최소 20초 지속
        self.MINIMUM_DATA_POINTS = 4                  # 최소 4개 데이터 포인트

    def detect_all_performance_problems(
        self,
        load_test_timeseries: List[Dict],
        resource_usage_timeseries: List[Dict] = None
    ) -> List[PerformanceProblem]:
        """
        모든 성능 문제를 종합적으로 탐지

        Args:
            load_test_timeseries: k6 부하테스트 시계열 데이터
                - timestamp: 시간
                - vus: 가상 사용자 수
                - tps: 초당 처리량
                - avg_response_time: 평균 응답시간 (ms)
                - error_rate: 에러율 (%)

            resource_usage_timeseries: 리소스 사용량 시계열 데이터 (선택사항)
                - pod별 CPU/메모리 사용량 데이터

        Returns:
            탐지된 성능 문제 리스트
        """
        if not load_test_timeseries or len(load_test_timeseries) < self.MINIMUM_DATA_POINTS:
            logger.warning("부하테스트 데이터가 부족하여 성능 문제 탐지를 수행할 수 없습니다.")
            return []

        detected_problems = []

        try:
            # 데이터를 시간 순서로 정렬
            sorted_timeseries = sorted(load_test_timeseries, key=lambda x: x['timestamp'])

            logger.info(f"성능 문제 탐지 시작 - 데이터 포인트 {len(sorted_timeseries)}개")

            # 1. 응답시간 급증 패턴 탐지
            response_time_problems = self._detect_response_time_surge_patterns(sorted_timeseries)
            detected_problems.extend(response_time_problems)

            # 2. VUS 증가하지만 TPS 정체 패턴 탐지
            vus_tps_problems = self._detect_vus_increase_tps_stagnation_patterns(sorted_timeseries)
            detected_problems.extend(vus_tps_problems)

            # 3. 에러율 급증 패턴 탐지
            error_rate_problems = self._detect_error_rate_surge_patterns(sorted_timeseries)
            detected_problems.extend(error_rate_problems)

            # 4. 리소스 기반 성능 문제 탐지 (리소스 데이터가 있는 경우)
            if resource_usage_timeseries:
                resource_problems = self._detect_resource_based_performance_problems(
                    sorted_timeseries, resource_usage_timeseries
                )
                detected_problems.extend(resource_problems)

                # 5. 메트릭-자원 간 상관관계 종합 분석
                correlation_problems = self._detect_metric_resource_correlations(
                    sorted_timeseries, resource_usage_timeseries
                )
                detected_problems.extend(correlation_problems)

            logger.info(f"성능 문제 탐지 완료 - {len(detected_problems)}개 문제 발견")

        except Exception as e:
            logger.error(f"성능 문제 탐지 중 오류 발생: {e}")

        return detected_problems

    def _detect_response_time_surge_patterns(self, timeseries_data: List[Dict]) -> List[PerformanceProblem]:
        """
        응답시간 급증 패턴 탐지

        특정 시점부터 응답시간이 급격히 증가하여 지속되는 패턴을 찾습니다.
        이는 시스템이 처리 한계에 도달했음을 의미할 수 있습니다.

        Args:
            timeseries_data: 시간순으로 정렬된 부하테스트 데이터

        Returns:
            탐지된 응답시간 급증 문제들
        """
        problems = []

        # 최소 8개 데이터 포인트 필요 (40초)
        if len(timeseries_data) < 8:
            return problems

        # 초기 안정 구간의 평균 응답시간을 기준값으로 설정
        initial_stable_period = timeseries_data[:5]  # 처음 25초
        baseline_response_times = [
            point.get('avg_response_time', 0)
            for point in initial_stable_period
            if point.get('avg_response_time') is not None
        ]

        if not baseline_response_times:
            logger.warning("기준 응답시간을 계산할 수 없어 응답시간 급증 탐지를 건너뜁니다.")
            return problems

        baseline_avg_response_time = statistics.mean(baseline_response_times)

        if baseline_avg_response_time <= 0:
            logger.warning("기준 응답시간이 0 이하여서 응답시간 급증 탐지를 건너뜁니다.")
            return problems

        # 슬라이딩 윈도우로 급증 구간 탐지
        window_size = 4  # 20초 윈도우

        for i in range(5, len(timeseries_data) - window_size + 1):
            current_window = timeseries_data[i:i + window_size]

            # 현재 윈도우의 평균 응답시간 계산
            current_response_times = [
                point.get('avg_response_time', 0)
                for point in current_window
                if point.get('avg_response_time') is not None
            ]

            if len(current_response_times) < 3:  # 최소 3개 데이터 포인트
                continue

            current_avg_response_time = statistics.mean(current_response_times)

            # 응답시간 증가율 계산
            increase_rate_percent = ((current_avg_response_time - baseline_avg_response_time)
                                   / baseline_avg_response_time) * 100

            # 급증 조건 확인: 사용자 경험에 영향을 주는 경우만 탐지
            user_noticeable = current_avg_response_time > self.RESPONSE_TIME_USER_NOTICEABLE_MS
            significant_increase = increase_rate_percent > self.RESPONSE_TIME_INCREASE_THRESHOLD_PERCENT

            if user_noticeable and significant_increase:

                start_time = current_window[0]['timestamp']
                end_time = current_window[-1]['timestamp']
                duration = (end_time - start_time).total_seconds()

                # 심각도 레벨 결정
                if increase_rate_percent > 300:
                    severity = "critical"
                elif increase_rate_percent > 150:
                    severity = "warning"
                else:
                    severity = "normal"

                # 근본 원인 분석
                root_cause = self._analyze_response_time_surge_cause(
                    baseline_avg_response_time,
                    current_avg_response_time,
                    increase_rate_percent
                )

                # 탐지 근거 수집
                evidence = [
                    f"기준 응답시간: {baseline_avg_response_time:.1f}ms",
                    f"급증 후 응답시간: {current_avg_response_time:.1f}ms",
                    f"증가율: {increase_rate_percent:.1f}%",
                    f"지속 시간: {duration:.0f}초"
                ]

                # 성능 영향 분석
                impact_description = (
                    f"응답시간이 {increase_rate_percent:.1f}% 증가하여 "
                    f"사용자 경험에 심각한 영향을 미치고 있습니다."
                )

                # AI 프롬프트용 컨텍스트 생성 (시간 정보 포함)
                start_time_str = start_time.strftime("%H:%M:%S")
                end_time_str = end_time.strftime("%H:%M:%S")
                ai_context = (
                    f"**응답시간 급증 탐지 ({start_time_str}~{end_time_str})**: 기준값 {baseline_avg_response_time:.1f}ms에서 "
                    f"{current_avg_response_time:.1f}ms로 {increase_rate_percent:.1f}% 급증했습니다. "
                    f"{root_cause}"
                )

                problem = PerformanceProblem(
                    problem_type=PerformanceProblemType.RESPONSE_TIME_SPIKE,
                    severity_level=severity,
                    confidence_score=min(0.95, 0.7 + (increase_rate_percent / 400)),
                    started_at=start_time,
                    ended_at=end_time,
                    duration_seconds=duration,
                    root_cause_description=root_cause,
                    detected_evidence=evidence,
                    performance_impact=impact_description,
                    ai_prompt_context=ai_context,
                    metric_details={
                        "baseline_response_time_ms": baseline_avg_response_time,
                        "surge_response_time_ms": current_avg_response_time,
                        "increase_rate_percent": increase_rate_percent,
                        "duration_seconds": duration
                    }
                )

                problems.append(problem)

                # 중복 탐지 방지를 위해 윈도우 점프
                i += window_size // 2

        return problems

    def _analyze_response_time_surge_cause(
        self,
        baseline_ms: float,
        current_ms: float,
        increase_rate: float
    ) -> str:
        """
        응답시간 급증의 가능한 원인을 분석

        Args:
            baseline_ms: 기준 응답시간 (밀리초)
            current_ms: 현재 응답시간 (밀리초)
            increase_rate: 증가율 (퍼센트)

        Returns:
            가능한 원인에 대한 설명
        """
        if increase_rate > 500:
            return "시스템이 완전히 과부하 상태로, 즉시 부하 감소나 스케일링이 필요합니다."
        elif increase_rate > 200:
            return "CPU 과부하나 데이터베이스 병목이 의심됩니다. 리소스 모니터링을 확인하세요."
        elif baseline_ms < 100 and current_ms > 500:
            return "네트워크 지연이나 외부 API 의존성 문제가 의심됩니다."
        else:
            return "애플리케이션 레벨의 성능 병목이 발생했을 가능성이 높습니다."

    def _detect_vus_increase_tps_stagnation_patterns(self, timeseries_data: List[Dict]) -> List[PerformanceProblem]:
        """
        VUS 증가하지만 TPS 정체 패턴 탐지

        가상 사용자 수는 계속 증가하지만 실제 처리량(TPS)이 증가하지 않는
        패턴을 탐지합니다. 이는 시스템 처리 능력의 한계를 나타냅니다.

        Args:
            timeseries_data: 시간순으로 정렬된 부하테스트 데이터

        Returns:
            탐지된 VUS-TPS 불일치 문제들
        """
        problems = []

        # 최소 6개 데이터 포인트 필요 (30초)
        if len(timeseries_data) < 6:
            return problems

        # 슬라이딩 윈도우로 VUS-TPS 패턴 분석
        window_size = 6  # 30초 윈도우

        for i in range(len(timeseries_data) - window_size + 1):
            window = timeseries_data[i:i + window_size]

            # VUS와 TPS 데이터 추출
            vus_values = [point.get('vus', 0) for point in window if point.get('vus') is not None]
            tps_values = [point.get('tps', 0) for point in window if point.get('tps') is not None]

            if len(vus_values) < 5 or len(tps_values) < 5:
                continue

            # 시작점과 끝점의 값 비교
            vus_start = vus_values[0]
            vus_end = vus_values[-1]
            tps_start = tps_values[0]
            tps_end = tps_values[-1]

            if vus_start <= 0 or tps_start <= 0:
                continue

            # 변화율 계산
            vus_increase_rate = ((vus_end - vus_start) / vus_start) * 100
            tps_change_rate = ((tps_end - tps_start) / tps_start) * 100

            # VUS-TPS 불일치 조건 확인
            if (vus_increase_rate > self.VUS_INCREASE_THRESHOLD_PERCENT and
                tps_change_rate < self.TPS_STAGNATION_THRESHOLD_PERCENT):

                # VUS가 지속적으로 증가하는지 확인 (지속성 검증)
                vus_increasing_points = sum(
                    1 for j in range(1, len(vus_values))
                    if vus_values[j] >= vus_values[j-1]
                )

                # 최소 80% 이상의 포인트에서 VUS가 증가해야 함
                if vus_increasing_points < len(vus_values) * 0.8:
                    continue

                start_time = window[0]['timestamp']
                end_time = window[-1]['timestamp']
                duration = (end_time - start_time).total_seconds()

                # 심각도 판정
                if vus_increase_rate > 80 and tps_change_rate < 5:
                    severity = "critical"
                elif vus_increase_rate > 50:
                    severity = "warning"
                else:
                    severity = "normal"

                # 근본 원인 분석
                root_cause = self._analyze_vus_tps_mismatch_cause(vus_increase_rate, tps_change_rate)

                # 탐지 근거
                evidence = [
                    f"VUS 변화: {vus_start:.0f} → {vus_end:.0f} ({vus_increase_rate:.1f}% 증가)",
                    f"TPS 변화: {tps_start:.1f} → {tps_end:.1f} ({tps_change_rate:.1f}% 변화)",
                    f"VUS 지속 증가 비율: {(vus_increasing_points/len(vus_values)*100):.0f}%",
                    f"패턴 지속 시간: {duration:.0f}초"
                ]

                # 성능 영향
                impact = (
                    f"가상 사용자 {vus_increase_rate:.1f}% 증가에도 불구하고 "
                    f"처리량이 {tps_change_rate:.1f}%만 변화하여 시스템 처리 한계에 도달했습니다."
                )

                # AI 컨텍스트 (시간 정보 포함)
                start_time_str = start_time.strftime("%H:%M:%S")
                end_time_str = end_time.strftime("%H:%M:%S")
                ai_context = (
                    f"**시스템 처리 한계 탐지 ({start_time_str}~{end_time_str})**: VUS가 {vus_start:.0f}에서 {vus_end:.0f}로 "
                    f"{vus_increase_rate:.1f}% 증가했지만 TPS는 {tps_change_rate:.1f}%만 변화했습니다. "
                    f"{root_cause}"
                )

                problem = PerformanceProblem(
                    problem_type=PerformanceProblemType.VUS_TPS_MISMATCH,
                    severity_level=severity,
                    confidence_score=min(0.9, 0.6 + (vus_increase_rate / 100)),
                    started_at=start_time,
                    ended_at=end_time,
                    duration_seconds=duration,
                    root_cause_description=root_cause,
                    detected_evidence=evidence,
                    performance_impact=impact,
                    ai_prompt_context=ai_context,
                    metric_details={
                        "vus_start": vus_start,
                        "vus_end": vus_end,
                        "vus_increase_rate_percent": vus_increase_rate,
                        "tps_start": tps_start,
                        "tps_end": tps_end,
                        "tps_change_rate_percent": tps_change_rate,
                        "duration_seconds": duration
                    }
                )

                problems.append(problem)

                # 중복 탐지 방지
                i += window_size // 2

        return problems

    def _analyze_vus_tps_mismatch_cause(self, vus_increase_rate: float, tps_change_rate: float) -> str:
        """
        VUS-TPS 불일치의 가능한 원인 분석

        Args:
            vus_increase_rate: VUS 증가율 (퍼센트)
            tps_change_rate: TPS 변화율 (퍼센트)

        Returns:
            가능한 원인 설명
        """
        if tps_change_rate < 0:
            return "TPS가 감소하고 있어 시스템이 과부하 상태입니다. CPU나 메모리 리소스를 확인하세요."
        elif vus_increase_rate > 100 and tps_change_rate < 5:
            return "데이터베이스 커넥션 풀이나 스레드 풀 제한에 도달했을 가능성이 높습니다."
        elif vus_increase_rate > 50:
            return "CPU 병목이나 I/O 대기로 인한 처리 능력 한계가 의심됩니다."
        else:
            return "애플리케이션 로직의 동시성 처리 한계에 도달했을 수 있습니다."

    def _detect_error_rate_surge_patterns(self, timeseries_data: List[Dict]) -> List[PerformanceProblem]:
        """
        에러율 급증 패턴 탐지

        정상 범위를 벗어난 에러율 급증을 탐지합니다.

        Args:
            timeseries_data: 시간순으로 정렬된 부하테스트 데이터

        Returns:
            탐지된 에러율 급증 문제들
        """
        problems = []

        if len(timeseries_data) < 6:
            return problems

        # 초기 안정 구간의 기준 에러율 계산 (전체 데이터의 첫 1/3 또는 최소 3개)
        initial_period_size = max(3, len(timeseries_data) // 3)
        initial_error_rates = [
            point.get('error_rate', 0)
            for point in timeseries_data[:initial_period_size]
            if point.get('error_rate') is not None
        ]

        if not initial_error_rates:
            return problems

        baseline_error_rate = statistics.mean(initial_error_rates)

        # 슬라이딩 윈도우로 에러율 급증 구간 탐지
        window_size = 6  # 30초 윈도우

        for i in range(len(timeseries_data) - window_size + 1):
            window = timeseries_data[i:i + window_size]

            window_error_rates = [
                point.get('error_rate', 0)
                for point in window
                if point.get('error_rate') is not None
            ]

            if len(window_error_rates) < 4:
                continue

            avg_window_error_rate = statistics.mean(window_error_rates)
            max_window_error_rate = max(window_error_rates)

            # 에러율 급증 조건 확인
            error_spike_threshold = max(
                baseline_error_rate * 3,  # 기준의 3배
                self.ERROR_RATE_SPIKE_THRESHOLD_PERCENT  # 절대 임계값
            )

            if (avg_window_error_rate > error_spike_threshold and
                avg_window_error_rate > baseline_error_rate + 1):

                start_time = window[0]['timestamp']
                end_time = window[-1]['timestamp']
                duration = (end_time - start_time).total_seconds()

                # 심각도 판정
                if avg_window_error_rate > 15:
                    severity = "critical"
                elif avg_window_error_rate > 8:
                    severity = "warning"
                else:
                    severity = "normal"

                # 근본 원인 분석
                root_cause = self._analyze_error_rate_surge_cause(
                    baseline_error_rate, avg_window_error_rate, max_window_error_rate
                )

                # 탐지 근거
                evidence = [
                    f"기준 에러율: {baseline_error_rate:.2f}%",
                    f"급증 구간 평균 에러율: {avg_window_error_rate:.2f}%",
                    f"급증 구간 최대 에러율: {max_window_error_rate:.2f}%",
                    f"급증 배수: {(avg_window_error_rate / max(baseline_error_rate, 0.1)):.1f}배"
                ]

                # 성능 영향
                impact = (
                    f"에러율이 {avg_window_error_rate:.1f}%로 급증하여 "
                    f"서비스 안정성에 심각한 영향을 미치고 있습니다."
                )

                # AI 컨텍스트 (시간 정보 포함)
                start_time_str = start_time.strftime("%H:%M:%S")
                end_time_str = end_time.strftime("%H:%M:%S")
                ai_context = (
                    f"**에러율 급증 탐지 ({start_time_str}~{end_time_str})**: 기준 에러율 {baseline_error_rate:.1f}%에서 "
                    f"{avg_window_error_rate:.1f}%로 급증했습니다. {root_cause}"
                )

                problem = PerformanceProblem(
                    problem_type=PerformanceProblemType.ERROR_RATE_SURGE,
                    severity_level=severity,
                    confidence_score=min(0.95, 0.7 + (avg_window_error_rate / 20)),
                    started_at=start_time,
                    ended_at=end_time,
                    duration_seconds=duration,
                    root_cause_description=root_cause,
                    detected_evidence=evidence,
                    performance_impact=impact,
                    ai_prompt_context=ai_context,
                    metric_details={
                        "baseline_error_rate_percent": baseline_error_rate,
                        "surge_avg_error_rate_percent": avg_window_error_rate,
                        "surge_max_error_rate_percent": max_window_error_rate,
                        "spike_multiplier": avg_window_error_rate / max(baseline_error_rate, 0.1),
                        "duration_seconds": duration
                    }
                )

                problems.append(problem)

                # 중복 탐지 방지
                i += window_size // 2

        return problems

    def _analyze_error_rate_surge_cause(
        self,
        baseline_rate: float,
        surge_avg_rate: float,
        surge_max_rate: float
    ) -> str:
        """에러율 급증의 가능한 원인 분석"""

        if surge_max_rate > 50:
            return "시스템이 완전히 과부하 상태입니다. 즉시 부하를 줄이거나 서비스를 재시작하세요."
        elif surge_avg_rate > 20:
            return "메모리 부족이나 데이터베이스 연결 장애가 의심됩니다."
        elif surge_avg_rate > baseline_rate * 10:
            return "특정 기능의 장애나 외부 의존성 문제가 발생했을 가능성이 높습니다."
        else:
            return "일시적인 리소스 부족이나 네트워크 지연으로 인한 에러 증가로 보입니다."

    def _detect_resource_based_performance_problems(
        self,
        performance_timeseries: List[Dict],
        resource_timeseries: List[Dict]
    ) -> List[PerformanceProblem]:
        """
        리소스 사용량 기반 성능 문제 탐지

        CPU/메모리 사용량과 성능 지표의 상관관계를 분석하여
        리소스 기반 성능 문제를 탐지합니다.

        Args:
            performance_timeseries: 성능 데이터
            resource_timeseries: 리소스 사용량 데이터

        Returns:
            탐지된 리소스 기반 성능 문제들
        """
        problems = []

        # CPU 과부하 패턴 탐지
        cpu_problems = self._detect_cpu_overload_patterns(performance_timeseries, resource_timeseries)
        problems.extend(cpu_problems)

        # 메모리 고갈 패턴 탐지
        memory_problems = self._detect_memory_exhaustion_patterns(performance_timeseries, resource_timeseries)
        problems.extend(memory_problems)

        # OOM Kill 패턴 탐지
        oom_problems = self._detect_out_of_memory_kill_patterns(performance_timeseries, resource_timeseries)
        problems.extend(oom_problems)

        return problems

    def _detect_cpu_overload_patterns(
        self,
        performance_data: List[Dict],
        resource_data: List[Dict]
    ) -> List[PerformanceProblem]:
        """CPU 과부하로 인한 성능 저하 패턴 탐지"""

        problems = []

        # 시간 윈도우별 분석
        window_size = 6  # 30초 윈도우

        for i in range(len(performance_data) - window_size + 1):
            perf_window = performance_data[i:i + window_size]
            window_start = perf_window[0]['timestamp']
            window_end = perf_window[-1]['timestamp']

            # 해당 시간대의 리소스 데이터 수집
            matching_resources = self._get_resource_data_in_time_range(
                resource_data, window_start, window_end
            )

            if not matching_resources:
                continue

            # 성능 메트릭 계산
            avg_response_time = statistics.mean([
                p.get('avg_response_time', 0) for p in perf_window
                if p.get('avg_response_time') is not None
            ])

            # CPU 사용률 계산
            cpu_usages = []
            for resource in matching_resources:
                for point in resource.get('matched_usage_points', []):
                    if point.get('cpu_usage_percent') is not None:
                        cpu_usages.append(point['cpu_usage_percent'])

            if not cpu_usages:
                continue

            avg_cpu_usage = statistics.mean(cpu_usages)
            max_cpu_usage = max(cpu_usages)

            # CPU 과부하 + 성능 저하 조건 확인
            if (avg_cpu_usage > self.HIGH_CPU_USAGE_THRESHOLD_PERCENT and
                avg_response_time > 200):  # 응답시간도 지연되고 있는 경우

                duration = (window_end - window_start).total_seconds()

                # 심각도 판정
                if max_cpu_usage > 95:
                    severity = "critical"
                elif avg_cpu_usage > 90:
                    severity = "warning"
                else:
                    severity = "normal"

                root_cause = f"CPU 사용률 {avg_cpu_usage:.1f}%로 과부하 상태입니다."

                evidence = [
                    f"평균 CPU 사용률: {avg_cpu_usage:.1f}%",
                    f"최대 CPU 사용률: {max_cpu_usage:.1f}%",
                    f"평균 응답시간: {avg_response_time:.1f}ms",
                    f"영향받은 Pod 수: {len(matching_resources)}개"
                ]

                impact = f"높은 CPU 사용률로 인해 응답시간이 {avg_response_time:.1f}ms로 지연되고 있습니다."

                ai_context = (
                    f"**CPU 과부하 탐지**: 평균 CPU 사용률 {avg_cpu_usage:.1f}%로 "
                    f"과부하 상태이며, 응답시간이 {avg_response_time:.1f}ms로 지연되고 있습니다. "
                    f"CPU 집약적 작업 최적화나 수평 확장이 필요합니다."
                )

                problem = PerformanceProblem(
                    problem_type=PerformanceProblemType.CPU_OVERLOAD,
                    severity_level=severity,
                    confidence_score=0.85,
                    started_at=window_start,
                    ended_at=window_end,
                    duration_seconds=duration,
                    root_cause_description=root_cause,
                    detected_evidence=evidence,
                    performance_impact=impact,
                    ai_prompt_context=ai_context,
                    metric_details={
                        "avg_cpu_usage_percent": avg_cpu_usage,
                        "max_cpu_usage_percent": max_cpu_usage,
                        "avg_response_time_ms": avg_response_time,
                        "affected_pods_count": len(matching_resources)
                    }
                )

                problems.append(problem)

                # 중복 탐지 방지
                i += window_size // 2

        return problems

    def _detect_memory_exhaustion_patterns(
        self,
        performance_data: List[Dict],
        resource_data: List[Dict]
    ) -> List[PerformanceProblem]:
        """메모리 고갈로 인한 성능 문제 탐지"""

        problems = []

        # 구현 로직은 CPU 과부하와 유사하지만 메모리 메트릭 사용
        # 메모리 사용률이 높고 에러율이 증가하는 패턴을 탐지

        window_size = 6

        for i in range(len(performance_data) - window_size + 1):
            perf_window = performance_data[i:i + window_size]
            window_start = perf_window[0]['timestamp']
            window_end = perf_window[-1]['timestamp']

            matching_resources = self._get_resource_data_in_time_range(
                resource_data, window_start, window_end
            )

            if not matching_resources:
                continue

            # 에러율 계산
            avg_error_rate = statistics.mean([
                p.get('error_rate', 0) for p in perf_window
                if p.get('error_rate') is not None
            ])

            # 메모리 사용률 계산
            memory_usages = []
            for resource in matching_resources:
                for point in resource.get('matched_usage_points', []):
                    if point.get('memory_usage_percent') is not None:
                        memory_usages.append(point['memory_usage_percent'])

            if not memory_usages:
                continue

            avg_memory_usage = statistics.mean(memory_usages)
            max_memory_usage = max(memory_usages)

            # 메모리 고갈 + 에러 증가 조건
            if (avg_memory_usage > self.HIGH_MEMORY_USAGE_THRESHOLD_PERCENT and
                avg_error_rate > self.ERROR_RATE_SPIKE_THRESHOLD_PERCENT):

                duration = (window_end - window_start).total_seconds()

                severity = "critical" if max_memory_usage > 95 else "warning"

                root_cause = f"메모리 사용률 {avg_memory_usage:.1f}%로 고갈 위험 상태입니다."

                evidence = [
                    f"평균 메모리 사용률: {avg_memory_usage:.1f}%",
                    f"최대 메모리 사용률: {max_memory_usage:.1f}%",
                    f"평균 에러율: {avg_error_rate:.1f}%",
                    f"영향받은 Pod 수: {len(matching_resources)}개"
                ]

                impact = f"높은 메모리 사용률로 인해 에러율이 {avg_error_rate:.1f}%로 증가했습니다."

                ai_context = (
                    f"**메모리 고갈 탐지**: 메모리 사용률 {avg_memory_usage:.1f}%로 "
                    f"고갈 위험 상태이며, 에러율이 {avg_error_rate:.1f}%로 증가했습니다. "
                    f"메모리 누수 점검이나 힙 크기 조정이 필요합니다."
                )

                problem = PerformanceProblem(
                    problem_type=PerformanceProblemType.MEMORY_EXHAUSTION,
                    severity_level=severity,
                    confidence_score=0.90,
                    started_at=window_start,
                    ended_at=window_end,
                    duration_seconds=duration,
                    root_cause_description=root_cause,
                    detected_evidence=evidence,
                    performance_impact=impact,
                    ai_prompt_context=ai_context,
                    metric_details={
                        "avg_memory_usage_percent": avg_memory_usage,
                        "max_memory_usage_percent": max_memory_usage,
                        "avg_error_rate_percent": avg_error_rate,
                        "affected_pods_count": len(matching_resources)
                    }
                )

                problems.append(problem)
                i += window_size // 2

        return problems

    def _detect_out_of_memory_kill_patterns(
        self,
        performance_data: List[Dict],
        resource_data: List[Dict]
    ) -> List[PerformanceProblem]:
        """OOM Kill 패턴 탐지 - 메모리 급락과 에러 급증의 시간 상관관계"""

        problems = []

        # 에러율 급증 시점들 찾기
        error_spike_times = []
        for i in range(1, len(performance_data)):
            prev_error = performance_data[i-1].get('error_rate', 0)
            curr_error = performance_data[i].get('error_rate', 0)

            # 에러율이 급격히 증가한 시점
            if curr_error > prev_error + 3 and curr_error > 5:
                error_spike_times.append({
                    'timestamp': performance_data[i]['timestamp'],
                    'error_rate': curr_error
                })

        if not error_spike_times:
            return problems

        # 각 Pod의 메모리 급락 찾기
        for pod_data in resource_data:
            usage_data = pod_data.get('usage_data', [])
            if len(usage_data) < 10:
                continue

            # 메모리 급락 지점 탐지
            for i in range(5, len(usage_data) - 5):
                # 급락 전후 메모리 사용률 계산
                before_memory_points = usage_data[i-5:i]
                after_memory_points = usage_data[i:i+5]

                before_memory_values = [
                    point.get('memory_usage_percent', 0)
                    for point in before_memory_points
                    if point.get('memory_usage_percent') is not None
                ]

                after_memory_values = [
                    point.get('memory_usage_percent', 0)
                    for point in after_memory_points
                    if point.get('memory_usage_percent') is not None
                ]

                if not before_memory_values or not after_memory_values:
                    continue

                before_avg = statistics.mean(before_memory_values)
                after_avg = statistics.mean(after_memory_values)

                if before_avg <= 0:
                    continue

                # 메모리 급락률 계산
                memory_drop_rate = ((before_avg - after_avg) / before_avg) * 100
                memory_drop_time = usage_data[i]['timestamp']

                # 메모리 급락과 에러 급증의 시간 상관관계 확인
                for error_spike in error_spike_times:
                    time_diff = abs((memory_drop_time - error_spike['timestamp']).total_seconds())

                    # 45초 이내에 발생하고 메모리가 30% 이상 급락한 경우 (OOM Kill 허용 범위 확대)
                    if time_diff < 45 and memory_drop_rate > self.MEMORY_DROP_THRESHOLD_PERCENT:

                        problem = PerformanceProblem(
                            problem_type=PerformanceProblemType.OUT_OF_MEMORY_KILL,
                            severity_level="critical",
                            confidence_score=0.95,
                            started_at=min(memory_drop_time, error_spike['timestamp']),
                            ended_at=max(memory_drop_time, error_spike['timestamp']),
                            duration_seconds=time_diff,
                            root_cause_description="Out of Memory Kill (OOM) 발생으로 Pod가 강제 종료되었습니다.",
                            detected_evidence=[
                                f"Pod {pod_data.get('pod_name', 'unknown')}에서 메모리 {memory_drop_rate:.1f}% 급락",
                                f"동시간대 에러율 {error_spike['error_rate']:.1f}%로 급증",
                                f"시간 상관관계: {time_diff:.0f}초 이내 발생",
                                f"급락 전 메모리 사용률: {before_avg:.1f}%"
                            ],
                            performance_impact="OOM Kill로 인한 Pod 재시작으로 서비스 중단이 발생했습니다.",
                            ai_prompt_context=(
                                f"**OOM Kill 탐지**: Pod {pod_data.get('pod_name', 'unknown')}에서 "
                                f"메모리 부족으로 인한 강제 종료가 발생했습니다. "
                                f"메모리 사용률이 {memory_drop_rate:.1f}% 급락하면서 "
                                f"에러율이 {error_spike['error_rate']:.1f}%로 급증했습니다. "
                                f"메모리 할당량 증가가 시급합니다."
                            ),
                            metric_details={
                                "pod_name": pod_data.get('pod_name', 'unknown'),
                                "before_memory_percent": before_avg,
                                "after_memory_percent": after_avg,
                                "memory_drop_rate_percent": memory_drop_rate,
                                "concurrent_error_rate_percent": error_spike['error_rate'],
                                "time_correlation_seconds": time_diff
                            }
                        )

                        problems.append(problem)
                        break  # 하나의 Pod당 하나의 OOM Kill만 탐지

        return problems

    def _detect_metric_resource_correlations(
        self,
        performance_data: List[Dict],
        resource_data: List[Dict]
    ) -> List[PerformanceProblem]:
        """
        메트릭-자원 간 상관관계 종합 분석

        CPU/메모리 사용률과 성능 메트릭(응답시간, TPS, 에러율) 간의 상관관계를 분석하여
        리소스 병목으로 인한 성능 저하를 탐지합니다.
        """
        problems = []

        if len(performance_data) < 8 or not resource_data:
            return problems

        # 시간대별 성능-리소스 데이터 매칭
        time_matched_data = self._match_performance_resource_by_time(performance_data, resource_data)

        if len(time_matched_data) < 5:
            return problems

        # 1. CPU 사용률과 응답시간 상관관계 분석
        problems.extend(self._analyze_cpu_response_time_correlation(time_matched_data))

        # 2. 메모리 사용률과 TPS 상관관계 분석
        problems.extend(self._analyze_memory_tps_correlation(time_matched_data))

        # 3. 리소스 제한 근접과 에러율 상관관계 분석
        problems.extend(self._analyze_resource_limit_error_correlation(time_matched_data))

        # 4. 종합적인 리소스 포화 상태 분석
        problems.extend(self._analyze_resource_saturation_patterns(time_matched_data))

        return problems

    def _match_performance_resource_by_time(
        self,
        performance_data: List[Dict],
        resource_data: List[Dict]
    ) -> List[Dict]:
        """성능 데이터와 리소스 데이터를 시간 기준으로 매칭"""
        matched_data = []

        for perf_point in performance_data:
            perf_time = perf_point['timestamp']

            # 해당 시간대의 모든 Pod 리소스 평균 계산
            cpu_values = []
            memory_values = []
            cpu_limits = []
            memory_limits = []

            for pod_data in resource_data:
                for usage_point in pod_data.get('usage_data', []):
                    usage_time = usage_point['timestamp']
                    time_diff = abs((perf_time - usage_time).total_seconds())

                    # 5초 이내 데이터만 매칭
                    if time_diff <= 5:
                        cpu_values.append(usage_point.get('cpu_usage_percent', 0))
                        memory_values.append(usage_point.get('memory_usage_percent', 0))

                        # 리소스 제한값 추가 (있는 경우)
                        if usage_point.get('cpu_limit_millicores'):
                            cpu_limits.append(usage_point.get('cpu_limit_millicores', 0))
                        if usage_point.get('memory_limit_mb'):
                            memory_limits.append(usage_point.get('memory_limit_mb', 0))

            if cpu_values and memory_values:
                matched_point = {
                    'timestamp': perf_time,
                    'tps': perf_point.get('tps', 0),
                    'response_time': perf_point.get('avg_response_time', 0),
                    'error_rate': perf_point.get('error_rate', 0),
                    'vus': perf_point.get('vus', 0),
                    'avg_cpu_percent': statistics.mean(cpu_values),
                    'max_cpu_percent': max(cpu_values),
                    'avg_memory_percent': statistics.mean(memory_values),
                    'max_memory_percent': max(memory_values),
                    'cpu_limit_available': len(cpu_limits) > 0,
                    'memory_limit_available': len(memory_limits) > 0
                }
                matched_data.append(matched_point)

        return matched_data

    def _analyze_cpu_response_time_correlation(self, matched_data: List[Dict]) -> List[PerformanceProblem]:
        """CPU 사용률과 응답시간 상관관계 분석"""
        problems = []

        # CPU 80% 이상이면서 응답시간이 2배 이상 증가한 구간 탐지
        baseline_response_time = statistics.mean([
            point['response_time'] for point in matched_data[:3]
        ])

        high_correlation_count = 0
        correlation_start = None

        for i, point in enumerate(matched_data):
            cpu_high = point['avg_cpu_percent'] >= 80
            response_time_high = point['response_time'] >= baseline_response_time * 2

            if cpu_high and response_time_high:
                if correlation_start is None:
                    correlation_start = i
                high_correlation_count += 1
            else:
                if high_correlation_count >= 3:  # 3개 이상 연속 상관관계
                    problems.append(PerformanceProblem(
                        problem_type=PerformanceProblemType.CPU_OVERLOAD,
                        severity_level="warning",
                        confidence_score=0.85,
                        started_at=matched_data[correlation_start]['timestamp'],
                        ended_at=matched_data[i-1]['timestamp'],
                        duration_seconds=(i - correlation_start) * 5,
                        root_cause_description=f"CPU 과부하({point['max_cpu_percent']:.1f}%)로 인한 응답시간 증가가 감지되었습니다.",
                        detected_evidence=[
                            f"CPU 사용률 평균 {point['avg_cpu_percent']:.1f}%",
                            f"응답시간 {point['response_time']:.0f}ms (기준값 대비 {point['response_time']/baseline_response_time:.1f}배)"
                        ],
                        performance_impact=f"응답시간 {baseline_response_time:.0f}ms → {point['response_time']:.0f}ms 증가",
                        ai_prompt_context="CPU 과부하와 응답시간 상관관계 분석 결과를 반영하여 리소스 확장을 권장하세요.",
                        metric_details={
                            "cpu_usage_percent": point['avg_cpu_percent'],
                            "response_time_ms": point['response_time'],
                            "baseline_response_time_ms": baseline_response_time
                        }
                    ))

                high_correlation_count = 0
                correlation_start = None

        return problems

    def _analyze_memory_tps_correlation(self, matched_data: List[Dict]) -> List[PerformanceProblem]:
        """메모리 사용률과 TPS 상관관계 분석"""
        problems = []

        # 메모리 85% 이상이면서 TPS가 기준값의 70% 이하인 구간 탐지
        baseline_tps = statistics.mean([point['tps'] for point in matched_data[:3]])

        correlation_points = []

        for point in matched_data:
            memory_high = point['avg_memory_percent'] >= 85
            tps_low = point['tps'] <= baseline_tps * 0.7

            if memory_high and tps_low:
                correlation_points.append(point)

        if len(correlation_points) >= 3:
            start_point = correlation_points[0]
            end_point = correlation_points[-1]

            problems.append(PerformanceProblem(
                problem_type=PerformanceProblemType.MEMORY_EXHAUSTION,
                severity_level="warning",
                confidence_score=0.80,
                started_at=start_point['timestamp'],
                ended_at=end_point['timestamp'],
                duration_seconds=len(correlation_points) * 5,
                root_cause_description=f"메모리 고갈({end_point['max_memory_percent']:.1f}%)로 인한 TPS 감소가 감지되었습니다.",
                detected_evidence=[
                    f"메모리 사용률 평균 {end_point['avg_memory_percent']:.1f}%",
                    f"TPS {end_point['tps']:.1f} (기준값 대비 {end_point['tps']/baseline_tps:.1f}배)"
                ],
                performance_impact=f"TPS {baseline_tps:.1f} → {end_point['tps']:.1f} 감소",
                ai_prompt_context="메모리 부족으로 인한 TPS 저하 상관관계를 고려하여 메모리 확장을 권장하세요.",
                metric_details={
                    "memory_usage_percent": end_point['avg_memory_percent'],
                    "tps_current": end_point['tps'],
                    "tps_baseline": baseline_tps
                }
            ))

        return problems

    def _analyze_resource_limit_error_correlation(self, matched_data: List[Dict]) -> List[PerformanceProblem]:
        """리소스 제한 근접과 에러율 상관관계 분석"""
        problems = []

        # CPU/메모리 90% 이상이면서 에러율 증가 패턴 탐지
        baseline_error_rate = statistics.mean([point['error_rate'] for point in matched_data[:3]])

        for point in matched_data:
            resource_near_limit = (point['avg_cpu_percent'] >= 90 or point['avg_memory_percent'] >= 90)
            error_rate_high = point['error_rate'] >= baseline_error_rate * 3 and point['error_rate'] >= 5

            if resource_near_limit and error_rate_high:
                problems.append(PerformanceProblem(
                    problem_type=PerformanceProblemType.ERROR_RATE_SURGE,
                    severity_level="critical",
                    confidence_score=0.90,
                    started_at=point['timestamp'],
                    ended_at=point['timestamp'],
                    duration_seconds=5,
                    root_cause_description="리소스 제한 근접으로 인한 에러율 급증이 감지되었습니다.",
                    detected_evidence=[
                        f"CPU {point['avg_cpu_percent']:.1f}%, 메모리 {point['avg_memory_percent']:.1f}%",
                        f"에러율 {point['error_rate']:.1f}% (기준값 대비 {point['error_rate']/baseline_error_rate:.1f}배)"
                    ],
                    performance_impact=f"에러율 {baseline_error_rate:.1f}% → {point['error_rate']:.1f}% 증가",
                    ai_prompt_context="리소스 제한에 의한 에러율 급증을 고려하여 즉시 스케일 아웃을 권장하세요.",
                    metric_details={
                        "cpu_usage_percent": point['avg_cpu_percent'],
                        "memory_usage_percent": point['avg_memory_percent'],
                        "error_rate_percent": point['error_rate']
                    }
                ))

        return problems

    def _analyze_resource_saturation_patterns(self, matched_data: List[Dict]) -> List[PerformanceProblem]:
        """종합적인 리소스 포화 상태 분석"""
        problems = []

        # CPU + 메모리 동시 과부하와 전반적 성능 저하 패턴
        saturation_points = []

        for point in matched_data:
            # 리소스 포화 조건: CPU 75% 이상 AND 메모리 80% 이상
            cpu_saturated = point['avg_cpu_percent'] >= 75
            memory_saturated = point['avg_memory_percent'] >= 80

            if cpu_saturated and memory_saturated:
                saturation_points.append(point)

        if len(saturation_points) >= 4:  # 20초 이상 지속
            start_point = saturation_points[0]
            end_point = saturation_points[-1]

            # 성능 영향 계산
            avg_response_time = statistics.mean([p['response_time'] for p in saturation_points])
            avg_tps = statistics.mean([p['tps'] for p in saturation_points])
            avg_error_rate = statistics.mean([p['error_rate'] for p in saturation_points])

            problems.append(PerformanceProblem(
                problem_type=PerformanceProblemType.CPU_OVERLOAD,  # 대표 타입
                severity_level="critical",
                confidence_score=0.95,
                started_at=start_point['timestamp'],
                ended_at=end_point['timestamp'],
                duration_seconds=len(saturation_points) * 5,
                root_cause_description="CPU와 메모리 동시 포화로 인한 시스템 전반적 성능 저하가 감지되었습니다.",
                detected_evidence=[
                    f"CPU 평균 {end_point['avg_cpu_percent']:.1f}%, 메모리 평균 {end_point['avg_memory_percent']:.1f}%",
                    f"포화 상태 {len(saturation_points) * 5}초 지속",
                    f"응답시간 {avg_response_time:.0f}ms, TPS {avg_tps:.1f}, 에러율 {avg_error_rate:.1f}%"
                ],
                performance_impact="시스템 전반적 성능 저하 - 즉시 스케일링 필요",
                ai_prompt_context="CPU와 메모리 동시 포화 상태를 고려하여 긴급 리소스 확장과 시스템 최적화를 권장하세요.",
                metric_details={
                    "avg_cpu_percent": end_point['avg_cpu_percent'],
                    "avg_memory_percent": end_point['avg_memory_percent'],
                    "saturation_duration_seconds": len(saturation_points) * 5,
                    "avg_response_time_ms": avg_response_time,
                    "avg_tps": avg_tps,
                    "avg_error_rate_percent": avg_error_rate
                }
            ))

        return problems

    def _get_resource_data_in_time_range(
        self,
        resource_data: List[Dict],
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """
        특정 시간 범위에 해당하는 리소스 데이터 필터링

        Args:
            resource_data: 전체 리소스 데이터
            start_time: 시작 시간
            end_time: 종료 시간

        Returns:
            시간 범위에 맞는 리소스 데이터들
        """
        matching_resources = []

        for pod_resource in resource_data:
            usage_data = pod_resource.get('usage_data', [])

            # 시간 범위에 맞는 사용량 데이터 포인트들 필터링
            matched_points = []
            for point in usage_data:
                point_timestamp = point.get('timestamp')
                if point_timestamp and start_time <= point_timestamp <= end_time:
                    matched_points.append(point)

            # 매칭되는 포인트가 있으면 추가
            if matched_points:
                matching_resources.append({
                    **pod_resource,
                    'matched_usage_points': matched_points
                })

        return matching_resources

    def generate_ai_analysis_context(self, detected_problems: List[PerformanceProblem]) -> str:
        """
        AI 분석에 활용할 종합 컨텍스트 생성

        탐지된 모든 성능 문제들을 종합하여 AI가 근본 원인 분석과
        개선 방안을 제시할 수 있도록 구조화된 컨텍스트를 생성합니다.

        Args:
            detected_problems: 탐지된 성능 문제들

        Returns:
            AI 프롬프트에 포함할 컨텍스트 문자열
        """
        if not detected_problems:
            return ""

        context_parts = [
            "## 🔍 자동 탐지된 성능 문제 분석 결과\n",
            "시계열 데이터 분석을 통해 다음과 같은 성능 문제들이 탐지되었습니다:\n"
        ]

        # 1. 시간대별 문제 요약 추가
        timeline_summary = self._generate_timeline_summary(detected_problems)
        if timeline_summary:
            context_parts.extend([
                "## ⏰ 시간대별 문제 발생 타임라인",
                "",
                timeline_summary,
                ""
            ])

        # 2. 심각도별 상세 문제 분석
        context_parts.append("## 📋 탐지된 문제 상세 분석")
        context_parts.append("")

        # 심각도별로 정렬 (critical -> warning -> normal)
        severity_order = {"critical": 0, "warning": 1, "normal": 2}
        sorted_problems = sorted(detected_problems, key=lambda p: severity_order.get(p.severity_level, 3))

        for i, problem in enumerate(sorted_problems, 1):
            # 심각도 이모지
            severity_emoji = {
                "critical": "🚨",
                "warning": "⚠️",
                "normal": "ℹ️"
            }.get(problem.severity_level, "❓")

            # 문제 유형 한글명
            problem_type_names = {
                PerformanceProblemType.RESPONSE_TIME_SPIKE: "응답시간 급증",
                PerformanceProblemType.VUS_TPS_MISMATCH: "처리량 한계 도달",
                PerformanceProblemType.CPU_OVERLOAD: "CPU 과부하",
                PerformanceProblemType.MEMORY_EXHAUSTION: "메모리 고갈",
                PerformanceProblemType.ERROR_RATE_SURGE: "에러율 급증",
                PerformanceProblemType.OUT_OF_MEMORY_KILL: "OOM Kill 발생"
            }

            problem_name = problem_type_names.get(problem.problem_type, problem.problem_type.value)

            # 시간 정보 포맷팅
            start_time_str = problem.started_at.strftime("%H:%M:%S")
            end_time_str = problem.ended_at.strftime("%H:%M:%S")

            context_parts.append(f"### {i}. {severity_emoji} {problem_name} ({problem.severity_level})")
            context_parts.append(f"**발생 시간**: {start_time_str} ~ {end_time_str} ({problem.duration_seconds:.0f}초 지속)")
            context_parts.append(f"**신뢰도**: {problem.confidence_score:.0%}")
            context_parts.append(f"**설명**: {problem.root_cause_description}")
            if problem.ai_prompt_context:
                context_parts.append(f"**AI 분석 참고**: {problem.ai_prompt_context}")
            context_parts.append("")  # 빈 줄

        # 종합 분석 요청
        context_parts.extend([
            "## 📊 종합 분석 요청",
            "",
            "위에서 탐지된 성능 문제들을 종합하여 다음 사항들을 분석해주세요:",
            "",
            "1. **시간대별 패턴 분석**: 타임라인을 참고하여 문제 발생 순서와 연관성 분석",
            "2. **근본 원인 분석**: 탐지된 문제들의 상호 연관성과 근본적인 원인",
            "3. **우선순위**: 가장 먼저 해결해야 할 문제와 그 이유",
            "4. **구체적 개선 방안**: 각 문제별 실행 가능한 해결책",
            "5. **예방 조치**: 향후 동일한 문제 재발 방지 방안",
            "",
            "**중요**: 시간대별 발생 패턴과 탐지된 구체적인 수치를 근거로 하여 분석해주세요."
        ])

        return "\n".join(context_parts)

    def _generate_timeline_summary(self, detected_problems: List[PerformanceProblem]) -> str:
        """시간대별 문제 발생 타임라인 요약 생성 (중복 제거)"""
        if not detected_problems:
            return ""

        # 문제 유형 아이콘 매핑
        problem_icons = {
            PerformanceProblemType.RESPONSE_TIME_SPIKE: "⏱️",
            PerformanceProblemType.VUS_TPS_MISMATCH: "📈",
            PerformanceProblemType.CPU_OVERLOAD: "🔥",
            PerformanceProblemType.MEMORY_EXHAUSTION: "💾",
            PerformanceProblemType.ERROR_RATE_SURGE: "❌",
            PerformanceProblemType.OUT_OF_MEMORY_KILL: "💥"
        }

        # 문제 유형 축약명
        problem_short_names = {
            PerformanceProblemType.RESPONSE_TIME_SPIKE: "응답시간↑",
            PerformanceProblemType.VUS_TPS_MISMATCH: "TPS정체",
            PerformanceProblemType.CPU_OVERLOAD: "CPU과부하",
            PerformanceProblemType.MEMORY_EXHAUSTION: "메모리고갈",
            PerformanceProblemType.ERROR_RATE_SURGE: "에러율↑",
            PerformanceProblemType.OUT_OF_MEMORY_KILL: "OOM Kill"
        }

        # 유사한 문제들을 통합하여 중복 제거
        merged_problems = self._merge_overlapping_problems(detected_problems)

        # 시간 구간별 활성 문제 추적
        timeline_events = []

        # 모든 문제의 시작/끝 시점을 이벤트로 수집
        for problem in merged_problems:
            timeline_events.append({
                'time': problem.started_at,
                'type': 'start',
                'problem': problem
            })
            timeline_events.append({
                'time': problem.ended_at,
                'type': 'end',
                'problem': problem
            })

        # 시간순 정렬
        timeline_events.sort(key=lambda x: x['time'])

        # 시간대별 활성 문제 상태 추적
        active_problems = []
        timeline_parts = []
        last_time = None

        for event in timeline_events:
            current_time = event['time']

            # 문제 활성화/비활성화 처리
            if event['type'] == 'start':
                active_problems.append(event['problem'])
            else:
                if event['problem'] in active_problems:
                    active_problems.remove(event['problem'])

            # 1분 이상 차이날 때만 새로운 시간대로 간주하여 스냅샷 생성
            if last_time is None or (current_time - last_time).total_seconds() >= 60:
                if active_problems:  # 활성 문제가 있을 때만 타임라인에 추가
                    time_str = current_time.strftime("%H:%M")

                    # 활성 문제들을 심각도별로 정리
                    problem_summary = {}
                    for problem in active_problems:
                        icon = problem_icons.get(problem.problem_type, "❓")
                        short_name = problem_short_names.get(problem.problem_type, problem.problem_type.value)
                        severity = problem.severity_level

                        key = f"{icon} {short_name}"
                        if key not in problem_summary:
                            problem_summary[key] = {"count": 0, "max_severity": "normal"}

                        problem_summary[key]["count"] += 1

                        # 최고 심각도 업데이트
                        severity_priority = {"critical": 3, "warning": 2, "normal": 1}
                        if severity_priority.get(severity, 0) > severity_priority.get(problem_summary[key]["max_severity"], 0):
                            problem_summary[key]["max_severity"] = severity

                    # 요약 문자열 생성
                    summary_parts = []
                    for problem_key, info in problem_summary.items():
                        count = info["count"]
                        max_severity = info["max_severity"]
                        severity_mark = {"critical": "🚨", "warning": "⚠️", "normal": "ℹ️"}.get(max_severity, "")

                        if count > 1:
                            summary_parts.append(f"{problem_key}×{count}{severity_mark}")
                        else:
                            summary_parts.append(f"{problem_key}{severity_mark}")

                    if summary_parts:
                        timeline_parts.append(f"- **{time_str}**: {' | '.join(summary_parts)}")

                last_time = current_time

        # 마지막 활성 문제들도 타임라인에 추가 (만약 있다면)
        if active_problems and timeline_events:
            last_event_time = timeline_events[-1]['time']
            time_str = last_event_time.strftime("%H:%M")

            problem_summary = {}
            for problem in active_problems:
                icon = problem_icons.get(problem.problem_type, "❓")
                short_name = problem_short_names.get(problem.problem_type, problem.problem_type.value)
                severity = problem.severity_level

                key = f"{icon} {short_name}"
                if key not in problem_summary:
                    problem_summary[key] = {"count": 0, "max_severity": "normal"}

                problem_summary[key]["count"] += 1

                severity_priority = {"critical": 3, "warning": 2, "normal": 1}
                if severity_priority.get(severity, 0) > severity_priority.get(problem_summary[key]["max_severity"], 0):
                    problem_summary[key]["max_severity"] = severity

            summary_parts = []
            for problem_key, info in problem_summary.items():
                count = info["count"]
                max_severity = info["max_severity"]
                severity_mark = {"critical": "🚨", "warning": "⚠️", "normal": "ℹ️"}.get(max_severity, "")

                if count > 1:
                    summary_parts.append(f"{problem_key}×{count}{severity_mark}")
                else:
                    summary_parts.append(f"{problem_key}{severity_mark}")

            if summary_parts and f"- **{time_str}**:" not in "\n".join(timeline_parts):
                timeline_parts.append(f"- **{time_str}**: {' | '.join(summary_parts)}")

        return "\n".join(timeline_parts)

    def _merge_overlapping_problems(self, problems: List[PerformanceProblem]) -> List[PerformanceProblem]:
        """시간과 유형이 겹치는 유사한 문제들을 통합"""
        if not problems:
            return []

        # 문제 유형별로 그룹화
        problems_by_type = {}
        for problem in problems:
            if problem.problem_type not in problems_by_type:
                problems_by_type[problem.problem_type] = []
            problems_by_type[problem.problem_type].append(problem)

        merged_problems = []

        # 각 문제 유형별로 시간 겹침 처리
        for problem_type, type_problems in problems_by_type.items():
            # 시간순 정렬
            type_problems.sort(key=lambda p: p.started_at)

            if not type_problems:
                continue

            current_merged = type_problems[0]

            for next_problem in type_problems[1:]:
                # 시간이 겹치거나 5초 이내 간격이면 통합
                if (next_problem.started_at <= current_merged.ended_at or
                    (next_problem.started_at - current_merged.ended_at).total_seconds() <= 5):

                    # 통합: 더 넓은 시간 범위로 확장
                    merged_duration = (max(current_merged.ended_at, next_problem.ended_at) -
                                     min(current_merged.started_at, next_problem.started_at)).total_seconds()

                    # 통합된 AI 컨텍스트 생성 (중복 제거)
                    merged_ai_context = self._create_merged_ai_context(
                        current_merged, next_problem, merged_duration
                    )

                    current_merged = PerformanceProblem(
                        problem_type=current_merged.problem_type,
                        severity_level=self._get_higher_severity(current_merged.severity_level, next_problem.severity_level),
                        confidence_score=max(current_merged.confidence_score, next_problem.confidence_score),
                        started_at=min(current_merged.started_at, next_problem.started_at),
                        ended_at=max(current_merged.ended_at, next_problem.ended_at),
                        duration_seconds=merged_duration,
                        root_cause_description=current_merged.root_cause_description,
                        detected_evidence=list(set(current_merged.detected_evidence + next_problem.detected_evidence)),  # 중복 제거
                        performance_impact=current_merged.performance_impact,
                        ai_prompt_context=merged_ai_context,
                        metric_details={**current_merged.metric_details, **next_problem.metric_details}
                    )
                else:
                    # 겹치지 않으면 현재를 저장하고 새로운 것으로 시작
                    merged_problems.append(current_merged)
                    current_merged = next_problem

            # 마지막 문제 추가
            merged_problems.append(current_merged)

        return merged_problems

    def _create_merged_ai_context(
        self,
        problem1: PerformanceProblem,
        problem2: PerformanceProblem,
        merged_duration: float
    ) -> str:
        """통합된 AI 컨텍스트 생성 (중복 제거 및 요약)"""

        # 문제 유형 이름
        problem_type_names = {
            PerformanceProblemType.RESPONSE_TIME_SPIKE: "응답시간 급증",
            PerformanceProblemType.VUS_TPS_MISMATCH: "처리량 한계",
            PerformanceProblemType.CPU_OVERLOAD: "CPU 과부하",
            PerformanceProblemType.MEMORY_EXHAUSTION: "메모리 고갈",
            PerformanceProblemType.ERROR_RATE_SURGE: "에러율 급증",
            PerformanceProblemType.OUT_OF_MEMORY_KILL: "OOM Kill"
        }

        problem_name = problem_type_names.get(problem1.problem_type, problem1.problem_type.value)

        # 시간 정보
        start_time = min(problem1.started_at, problem2.started_at).strftime("%H:%M:%S")
        end_time = max(problem1.ended_at, problem2.ended_at).strftime("%H:%M:%S")

        # 주요 메트릭 값 추출 (중복되지 않는 핵심 정보만)
        key_metrics = []

        # 응답시간 관련
        if "baseline_response_time_ms" in problem1.metric_details:
            baseline = problem1.metric_details.get("baseline_response_time_ms", 0)
            surge = problem1.metric_details.get("surge_response_time_ms", 0)
            if baseline > 0 and surge > 0:
                increase_rate = ((surge - baseline) / baseline) * 100
                key_metrics.append(f"응답시간 {baseline:.1f}ms → {surge:.1f}ms ({increase_rate:.0f}% 증가)")

        # CPU/메모리 관련
        if "avg_cpu_percent" in problem1.metric_details:
            cpu = problem1.metric_details["avg_cpu_percent"]
            key_metrics.append(f"CPU {cpu:.1f}%")

        if "avg_memory_percent" in problem1.metric_details:
            memory = problem1.metric_details["avg_memory_percent"]
            key_metrics.append(f"메모리 {memory:.1f}%")

        # TPS 관련
        if "tps_current" in problem1.metric_details:
            tps = problem1.metric_details["tps_current"]
            key_metrics.append(f"TPS {tps:.1f}")

        # 에러율 관련
        if "surge_avg_error_rate_percent" in problem1.metric_details:
            error_rate = problem1.metric_details["surge_avg_error_rate_percent"]
            key_metrics.append(f"에러율 {error_rate:.1f}%")

        # 통합 컨텍스트 생성
        metrics_summary = " | ".join(key_metrics) if key_metrics else "상세 메트릭 정보 확인 필요"

        return (
            f"**{problem_name} 지속 탐지**: {start_time}~{end_time} ({merged_duration:.0f}초 지속) "
            f"- {metrics_summary}. "
            f"{problem1.root_cause_description}"
        )

    def _get_higher_severity(self, severity1: str, severity2: str) -> str:
        """두 심각도 중 더 높은 것 반환"""
        severity_priority = {"critical": 3, "warning": 2, "normal": 1}
        if severity_priority.get(severity1, 0) >= severity_priority.get(severity2, 0):
            return severity1
        return severity2


def get_performance_bottleneck_detector() -> PerformanceBottleneckDetector:
    """
    PerformanceBottleneckDetector 싱글톤 인스턴스 반환

    Returns:
        PerformanceBottleneckDetector 인스턴스
    """
    if not hasattr(get_performance_bottleneck_detector, "_instance"):
        get_performance_bottleneck_detector._instance = PerformanceBottleneckDetector()
        logger.info("PerformanceBottleneckDetector 인스턴스가 생성되었습니다.")

    return get_performance_bottleneck_detector._instance