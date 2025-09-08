import pytz
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload

from app.db.sqlite.models.history_models import TestHistoryModel, ScenarioHistoryModel, StageHistoryModel, TestParameterHistoryModel, TestHeaderHistoryModel, TestMetricsTimeseriesModel, TestResourceTimeseriesModel
from app.db.sqlite.models.project_models import ProjectModel, OpenAPISpecModel, EndpointModel
from app.dto.load_test.load_test_request import LoadTestRequest
from app.services.project.service import get_project_by_endpoint_id_simple
from app.dto.test_history.test_history_detail_response import (
    TestHistoryDetailResponse,
    ScenarioHistoryDetailResponse,
    StageHistoryDetailResponse,
    EndpointDetailResponse,
    OverallMetricsResponse,
    MetricGroupResponse,
    ResponseTimeMetricResponse,
    VusMetricResponse,
    TestParameterHistoryResponse,
    TestHeaderHistoryResponse
)
from app.dto.test_history.test_history_timeseries_response import (
    TestHistoryTimeseriesResponse,
    OverallTimeseriesResponse,
    ScenarioTimeseriesResponse,
    TimeseriesDataPoint
)

logger = logging.getLogger(__name__)
kst = pytz.timezone('Asia/Seoul')

def save_test_history(
    request: LoadTestRequest,
    k6_script_file_name: str,
    job_name: str,
    db: Session,
):
    # Project 조회 (반정규화)
    first_endpoint_id = request.scenarios[0].endpoint_id
    project = get_project_by_endpoint_id_simple(db, first_endpoint_id)

    # TestHistory 생성
    test_history = TestHistoryModel(
        title=request.title,
        description=request.description,
        target_tps=request.target_tps,
        tested_at=datetime.now(kst),
        job_name=job_name,
        k6_script_file_name=k6_script_file_name,
        project_id=project.id,
    )

    # 3. Scenario + Stage 저장
    for scenario in request.scenarios:
        scenario_model = ScenarioHistoryModel(
            name=scenario.name,
            scenario_tag=f'{job_name}{scenario.endpoint_id}',
            endpoint_id=scenario.endpoint_id,
            executor=scenario.executor,
            think_time=scenario.think_time,
            response_time_target=scenario.response_time_target,
            error_rate_target=scenario.error_rate_target
        )

        # Stage 저장
        for stage in scenario.stages:
            stage_model = StageHistoryModel(
                duration=stage.duration,
                target=stage.target
            )
            scenario_model.stages.append(stage_model)
        
        # 파라미터 저장
        if scenario.parameters:
            for param in scenario.parameters:
                param_model = TestParameterHistoryModel(
                    name=param.name,
                    param_type=param.param_type,
                    value=param.value
                )
                scenario_model.test_parameters.append(param_model)
        
        # 헤더 저장
        if scenario.headers:
            for header in scenario.headers:
                header_model = TestHeaderHistoryModel(
                    header_key=header.header_key,
                    header_value=header.header_value
                )
                scenario_model.test_headers.append(header_model)

        test_history.scenarios.append(scenario_model)

    # 4. 최종 저장
    db.add(test_history)
    db.commit()
    db.refresh(test_history)

    return test_history


def get_test_histories(db: Session, skip: int = 0, limit: int = 100) -> List[TestHistoryModel]:
    return (
        db.query(TestHistoryModel)
        .options(
            joinedload(TestHistoryModel.scenarios)
            .joinedload(ScenarioHistoryModel.stages),
            joinedload(TestHistoryModel.scenarios)
            .joinedload(ScenarioHistoryModel.endpoint),
            joinedload(TestHistoryModel.scenarios)
            .joinedload(ScenarioHistoryModel.test_parameters),
            joinedload(TestHistoryModel.scenarios)
            .joinedload(ScenarioHistoryModel.test_headers)
        )
        .order_by(TestHistoryModel.tested_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_test_history_by_id(db: Session, test_history_id: int) -> Optional[TestHistoryModel]:
    return (
        db.query(TestHistoryModel)
        .options(
            joinedload(TestHistoryModel.scenarios)
            .joinedload(ScenarioHistoryModel.stages),
            joinedload(TestHistoryModel.scenarios)
            .joinedload(ScenarioHistoryModel.endpoint),
            joinedload(TestHistoryModel.scenarios)
            .joinedload(ScenarioHistoryModel.test_parameters),
            joinedload(TestHistoryModel.scenarios)
            .joinedload(ScenarioHistoryModel.test_headers)
        )
        .filter(TestHistoryModel.id == test_history_id)
        .first()
    )


def get_test_history_by_job_name(db: Session, job_name: str) -> Optional[TestHistoryModel]:
    """Job 이름으로 테스트 히스토리를 조회합니다."""
    return (
        db.query(TestHistoryModel)
        .options(
            joinedload(TestHistoryModel.scenarios)
            .joinedload(ScenarioHistoryModel.stages),
            joinedload(TestHistoryModel.scenarios)
            .joinedload(ScenarioHistoryModel.endpoint),
            joinedload(TestHistoryModel.scenarios)
            .joinedload(ScenarioHistoryModel.test_parameters),
            joinedload(TestHistoryModel.scenarios)
            .joinedload(ScenarioHistoryModel.test_headers)
        )
        .filter(TestHistoryModel.job_name == job_name)
        .first()
    )


def update_test_history_final_metrics(
    db: Session,
    job_name: str,
    overall_metrics: Dict[str, Any],
    scenario_metrics: Dict[str, Dict[str, Any]] = None
) -> bool:
    """
    테스트 완료 후 최종 메트릭으로 테스트 히스토리를 업데이트합니다.
    
    Args:
        db: 데이터베이스 세션
        job_name: k6 Job 이름
        overall_metrics: 전체 테스트 메트릭
        scenario_metrics: 시나리오별 메트릭 (선택사항)
        
    Returns:
        업데이트 성공 여부
    """
    try:
        # 테스트 히스토리 조회
        test_history = get_test_history_by_job_name(db, job_name)
        if not test_history:
            logger.error(f"Test history not found for job: {job_name}")
            return False
        
        # 전체 테스트 메트릭 업데이트 - InfluxDB 플랫 구조에 맞게 수정
        test_history.is_completed = True
        test_history.completed_at = datetime.now(kst)
        
        # TPS 메트릭 (현재는 단일 값만 있으므로 max/min/avg에 동일값 설정)
        if 'actual_tps' in overall_metrics:
            tps_value = float(overall_metrics['actual_tps'])
            test_history.max_tps = tps_value
            test_history.min_tps = tps_value
            test_history.avg_tps = tps_value
        
        # Response Time 메트릭
        test_history.avg_response_time = float(overall_metrics.get('avg_response_time', 0.0))
        test_history.max_response_time = float(overall_metrics.get('max_response_time', 0.0))
        test_history.min_response_time = float(overall_metrics.get('min_response_time', 0.0))
        test_history.p95_response_time = float(overall_metrics.get('p95_response_time', 0.0))
        
        # p50, p99는 InfluxDB에서 현재 제공하지 않으므로 0으로 설정하거나 계산된 값 사용
        test_history.p50_response_time = float(overall_metrics.get('p50_response_time', 0.0))
        test_history.p99_response_time = float(overall_metrics.get('p99_response_time', 0.0))
        
        # Error Rate 메트릭 (현재는 단일 값만 있으므로 max/min/avg에 동일값 설정)
        if 'error_rate' in overall_metrics:
            error_rate_value = float(overall_metrics['error_rate'])
            test_history.max_error_rate = error_rate_value
            test_history.min_error_rate = error_rate_value
            test_history.avg_error_rate = error_rate_value
        
        # VUS 메트릭 (현재는 max_vus만 있음)
        if 'max_vus' in overall_metrics:
            vus_value = int(overall_metrics['max_vus'])
            test_history.max_vus = vus_value
            test_history.min_vus = vus_value  # 임시로 동일값 설정
            test_history.avg_vus = float(vus_value)  # 임시로 동일값 설정
        
        # 기타 메트릭
        test_history.total_requests = int(overall_metrics.get('total_requests', 0))
        test_history.failed_requests = int(overall_metrics.get('failed_requests', 0))
        test_history.test_duration = float(overall_metrics.get('test_duration', 0.0))
        
        # 시나리오별 메트릭 업데이트 - InfluxDB 플랫 구조에 맞게 수정
        if scenario_metrics:
            for scenario in test_history.scenarios:
                scenario_key = scenario.scenario_tag  # scenario_name 대신 scenario_tag 사용
                if scenario_key in scenario_metrics:
                    metrics = scenario_metrics[scenario_key]
                    
                    # TPS 메트릭 (현재는 단일 값만 있으므로 max/min/avg에 동일값 설정)
                    if 'tps' in metrics:
                        tps_value = float(metrics['tps'])
                        scenario.max_tps = tps_value
                        scenario.min_tps = tps_value
                        scenario.avg_tps = tps_value
                    
                    # Response Time 메트릭
                    scenario.avg_response_time = float(metrics.get('avg_response_time', 0.0))
                    scenario.max_response_time = float(metrics.get('max_response_time', 0.0))
                    scenario.min_response_time = float(metrics.get('min_response_time', 0.0))
                    scenario.p95_response_time = float(metrics.get('p95_response_time', 0.0))
                    
                    # p50, p99는 InfluxDB에서 현재 제공하지 않으므로 0으로 설정하거나 계산된 값 사용
                    scenario.p50_response_time = float(metrics.get('p50_response_time', 0.0))
                    scenario.p99_response_time = float(metrics.get('p99_response_time', 0.0))
                    
                    # Error Rate 메트릭 (현재는 단일 값만 있으므로 max/min/avg에 동일값 설정)
                    if 'error_rate' in metrics:
                        error_rate_value = float(metrics['error_rate'])
                        scenario.max_error_rate = error_rate_value
                        scenario.min_error_rate = error_rate_value
                        scenario.avg_error_rate = error_rate_value
                    
                    # VUS 메트릭 (시나리오별 VUS는 InfluxDB에서 현재 제공하지 않음 - 0으로 설정)
                    scenario.max_vus = int(metrics.get('max_vus', 0))
                    scenario.min_vus = int(metrics.get('min_vus', 0))
                    scenario.avg_vus = float(metrics.get('avg_vus', 0.0))
                    
                    # 기타 메트릭
                    scenario.total_requests = int(metrics.get('total_requests', 0))
                    scenario.failed_requests = int(metrics.get('failed_requests', 0))
                    scenario.test_duration = float(metrics.get('test_duration', 0.0))
        
        # 데이터베이스 커밋
        db.commit()
        db.refresh(test_history)
        
        logger.info(f"Successfully updated final metrics for job: {job_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating final metrics for job {job_name}: {e}")
        db.rollback()
        return False


def get_incomplete_test_histories(db: Session) -> List[TestHistoryModel]:
    """완료되지 않은 테스트 히스토리 목록을 조회합니다."""
    return (
        db.query(TestHistoryModel)
        .filter(TestHistoryModel.is_completed == False)
        .order_by(TestHistoryModel.tested_at.desc())
        .all()
    )


def get_test_histories_with_project_info(db: Session, page: int = 0, size: int = 100):
    """프로젝트 정보와 함께 테스트 기록을 조회합니다."""
    # 서브쿼리로 프로젝트 정보를 가져옵니다
    return db.query(TestHistoryModel) \
        .join(TestHistoryModel.project) \
        .options(joinedload(TestHistoryModel.project)) \
        .order_by(TestHistoryModel.tested_at.desc()) \
        .offset(page * size) \
        .limit(size) \
        .all()


def get_test_histories_by_project_id(db: Session, project_id: int) -> List[TestHistoryModel]:
    """특정 프로젝트의 테스트 기록을 조회합니다."""
    results = (
        db.query(TestHistoryModel)
        .join(TestHistoryModel.project)
        .options(joinedload(TestHistoryModel.project))
        .filter(TestHistoryModel.project_id == project_id)
        .order_by(TestHistoryModel.tested_at.desc())
        .all()
    )

    return results


def build_test_history_detail_response(test_history: TestHistoryModel) -> TestHistoryDetailResponse:
    """TestHistoryModel을 응답 형식으로 변환합니다."""

    # Overall 메트릭 구성
    overall = OverallMetricsResponse(
        target_tps=test_history.target_tps,
        total_requests=test_history.total_requests,
        failed_requests=test_history.failed_requests,
        test_duration=test_history.test_duration,
        tps=MetricGroupResponse(
            max=test_history.max_tps,
            min=test_history.min_tps,
            avg=test_history.avg_tps
        ) if any([test_history.max_tps, test_history.min_tps, test_history.avg_tps]) else None,
        response_time=ResponseTimeMetricResponse(
            max=test_history.max_response_time,
            min=test_history.min_response_time,
            avg=test_history.avg_response_time,
            p50=test_history.p50_response_time,
            p95=test_history.p95_response_time,
            p99=test_history.p99_response_time
        ) if any([
            test_history.max_response_time, test_history.min_response_time,
            test_history.avg_response_time, test_history.p50_response_time,
            test_history.p95_response_time, test_history.p99_response_time
        ]) else None,
        error_rate=MetricGroupResponse(
            max=test_history.max_error_rate,
            min=test_history.min_error_rate,
            avg=test_history.avg_error_rate
        ) if any([x is not None for x in [test_history.max_error_rate, test_history.min_error_rate, test_history.avg_error_rate]]) else None,
        vus=VusMetricResponse(
            max=test_history.max_vus,
            min=test_history.min_vus,
            avg=test_history.avg_vus
        ) if any([test_history.max_vus, test_history.min_vus, test_history.avg_vus]) else None
    )

    # 시나리오 목록 구성
    scenarios = []
    for scenario in test_history.scenarios:
        # 엔드포인트 정보
        endpoint = None
        if scenario.endpoint:
            endpoint = EndpointDetailResponse(
                endpoint_id=scenario.endpoint.id,
                method=scenario.endpoint.method,
                path=scenario.endpoint.path,
                description=scenario.endpoint.description,
                summary=scenario.endpoint.summary
            )

        # 스테이지 목록
        stages = [
            StageHistoryDetailResponse(
                stage_history_id=stage.id,
                duration=stage.duration,
                target=stage.target
            ) for stage in scenario.stages
        ]

        # 파라미터 목록
        test_parameters = [
            TestParameterHistoryResponse(
                id=param.id,
                name=param.name,
                param_type=param.param_type,
                value=param.value
            ) for param in scenario.test_parameters or []
        ]

        # 헤더 목록
        test_headers = [
            TestHeaderHistoryResponse(
                id=header.id,
                header_key=header.header_key,
                header_value=header.header_value
            ) for header in scenario.test_headers or []
        ]

        # 시나리오 응답 구성
        scenario_response = ScenarioHistoryDetailResponse(
            scenario_history_id=scenario.id,
            name=scenario.name,
            scenario_tag=scenario.scenario_tag,
            total_requests=scenario.total_requests,
            failed_requests=scenario.failed_requests,
            test_duration=scenario.test_duration,
            response_time_target=scenario.response_time_target,
            error_rate_target=scenario.error_rate_target,
            think_time=scenario.think_time,
            executor=scenario.executor,
            endpoint=endpoint,
            tps=MetricGroupResponse(
                max=scenario.max_tps,
                min=scenario.min_tps,
                avg=scenario.avg_tps
            ) if any([scenario.max_tps, scenario.min_tps, scenario.avg_tps]) else None,
            response_time=ResponseTimeMetricResponse(
                max=scenario.max_response_time,
                min=scenario.min_response_time,
                avg=scenario.avg_response_time,
                p50=scenario.p50_response_time,
                p95=scenario.p95_response_time,
                p99=scenario.p99_response_time
            ) if any([
                scenario.max_response_time, scenario.min_response_time,
                scenario.avg_response_time, scenario.p50_response_time,
                scenario.p95_response_time, scenario.p99_response_time
            ]) else None,
            error_rate=MetricGroupResponse(
                max=scenario.max_error_rate,
                min=scenario.min_error_rate,
                avg=scenario.avg_error_rate
            ) if any([x is not None for x in [scenario.max_error_rate, scenario.min_error_rate, scenario.avg_error_rate]]) else None,
            stages=stages,
            test_parameters=test_parameters,
            test_headers=test_headers
        )
        scenarios.append(scenario_response)

    # 최종 응답 구성
    return TestHistoryDetailResponse(
        test_history_id=test_history.id,
        project_id=test_history.project_id,
        title=test_history.title,
        description=test_history.description,
        is_completed=test_history.is_completed,
        completed_at=test_history.completed_at,
        tested_at=test_history.tested_at,
        job_name=test_history.job_name,
        k6_script_file_name=test_history.k6_script_file_name,
        overall=overall,
        scenarios=scenarios
    )


# === 스케줄러용 추가 함수들 ===

def get_scenario_histories_by_test_id(db: Session, test_id: int) -> List[ScenarioHistoryModel]:
    """test_id로 관련 scenario_history들 조회 (여러 개 가능)"""
    return (
        db.query(ScenarioHistoryModel)
        .filter(ScenarioHistoryModel.test_history_id == test_id)
        .all()
    )


def update_test_history_with_metrics(db: Session, test_history: TestHistoryModel, metrics: Dict[str, Any]) -> bool:
    """test_history에 메트릭 업데이트 - InfluxDB 플랫 구조에 맞게 수정"""
    try:
        # metrics가 None인 경우 안전한 처리
        if metrics is None:
            logger.warning(f"Metrics is None for test_history: {test_history.job_name} - skipping update")
            return False
        # InfluxDB에서 반환하는 플랫 구조를 처리
        # TPS 메트릭 (현재는 단일 값만 있으므로 max/min/avg에 동일값 설정)
        test_history.max_tps = float(metrics.get('max_tps', 0.0))
        test_history.min_tps = float(metrics.get('min_tps', 0.0))
        test_history.avg_tps = float(metrics.get('avg_tps', 0.0))
        
        # Response Time 메트릭 업데이트
        test_history.avg_response_time = float(metrics.get('avg_response_time', 0.0))
        test_history.max_response_time = float(metrics.get('max_response_time', 0.0))
        test_history.min_response_time = float(metrics.get('min_response_time', 0.0))
        test_history.p50_response_time = float(metrics.get('p50_response_time', 0.0))
        test_history.p95_response_time = float(metrics.get('p95_response_time', 0.0))
        test_history.p99_response_time = float(metrics.get('p99_response_time', 0.0))
        
        # Error Rate 메트릭
        test_history.max_error_rate = float(metrics.get('max_error_rate', 0.0))
        test_history.min_error_rate = float(metrics.get('min_error_rate', 0.0))
        test_history.avg_error_rate = float(metrics.get('avg_error_rate', 0.0))
        
        # VUS 메트릭
        test_history.max_vus = float(metrics.get('max_vus', 0.0))
        test_history.min_vus = float(metrics.get('min_vus', 0.0))
        test_history.avg_vus = float(metrics.get('avg_vus', 0.0))
        
        # 기타 메트릭
        test_history.total_requests = int(metrics.get('total_requests', 0))
        test_history.failed_requests = int(metrics.get('failed_requests', 0))
        test_history.test_duration = float(metrics.get('test_duration', 0.0))
        
        db.commit()
        db.refresh(test_history)
        
        logger.info(f"Updated test_history metrics for job: {test_history.job_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating test_history metrics: {e}")
        db.rollback()
        return False


def update_scenario_history_with_metrics(db: Session, scenario_history: ScenarioHistoryModel, metrics: Dict[str, Any]) -> bool:
    """
    scenario_history에 모든 메트릭 정보를 업데이트
    
    Args:
        db: 데이터베이스 세션
        scenario_history: 업데이트할 시나리오 히스토리 모델
        metrics: InfluxDB에서 조회한 메트릭 데이터 딕셔너리
                - total_requests: 총 요청 수
                - failed_requests: 실패한 요청 수
                - max_tps, min_tps, avg_tps: TPS 통계
                - avg_response_time, max_response_time, min_response_time: 응답 시간 통계
                - p50_response_time, p95_response_time, p99_response_time: 응답 시간 백분위수
                - max_error_rate, min_error_rate, avg_error_rate: 에러율 통계
                - max_vus, min_vus, avg_vus: 가상 사용자 수 통계
                - test_duration: 테스트 지속 시간
                
    Returns:
        bool: 업데이트 성공 여부
    """
    try:
        # metrics가 None인 경우 안전한 처리
        if metrics is None:
            logger.warning(f"Metrics is None for scenario_history endpoint_id: {scenario_history.endpoint_id} - skipping update")
            return False
            
        # TPS 메트릭
        scenario_history.max_tps = float(metrics.get('max_tps', 0.0))
        scenario_history.min_tps = float(metrics.get('min_tps', 0.0))
        scenario_history.avg_tps = float(metrics.get('avg_tps', 0.0))
        
        # Response Time 메트릭 - 모든 백분위수 포함
        scenario_history.avg_response_time = float(metrics.get('avg_response_time', 0.0))
        scenario_history.max_response_time = float(metrics.get('max_response_time', 0.0))
        scenario_history.min_response_time = float(metrics.get('min_response_time', 0.0))
        scenario_history.p50_response_time = float(metrics.get('p50_response_time', 0.0))
        scenario_history.p95_response_time = float(metrics.get('p95_response_time', 0.0))
        scenario_history.p99_response_time = float(metrics.get('p99_response_time', 0.0))
        
        # Error Rate 메트릭 - 통계적 정보 포함
        scenario_history.max_error_rate = float(metrics.get('max_error_rate', 0.0))
        scenario_history.min_error_rate = float(metrics.get('min_error_rate', 0.0))
        scenario_history.avg_error_rate = float(metrics.get('avg_error_rate', 0.0))
        
        # 기타 메트릭 정보
        scenario_history.total_requests = int(metrics.get('total_requests', 0))
        scenario_history.failed_requests = int(metrics.get('failed_requests', 0))
        scenario_history.test_duration = float(metrics.get('test_duration', 0.0))
        
        db.commit()
        db.refresh(scenario_history)
        
        logger.info(f"Updated scenario_history metrics for endpoint_id: {scenario_history.endpoint_id} with all metric types")
        return True
        
    except Exception as e:
        logger.error(f"Error updating scenario_history metrics: {e}")
        db.rollback()
        return False


def mark_test_as_completed(db: Session, test_history: TestHistoryModel) -> bool:
    """테스트를 완료 상태로 마킹"""
    try:
        test_history.is_completed = True
        test_history.completed_at = datetime.now(kst)
        
        db.commit()
        db.refresh(test_history)
        
        logger.info(f"Marked test as completed for job: {test_history.job_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error marking test as completed: {e}")
        db.rollback()
        return False


# === 시계열 메트릭 관련 함수들 ===

def save_test_timeseries_metrics(db: Session, scenario_histories: List[ScenarioHistoryModel], timeseries_data: List[Dict]) -> bool:
    """
    테스트 완료 후 시계열 메트릭 데이터를 저장
    
    Args:
        db: 데이터베이스 세션
        scenario_histories: 시나리오 히스토리 리스트
        timeseries_data: InfluxDB에서 조회한 시계열 데이터 리스트
                       [
                           {
                               'timestamp': datetime,
                               'scenario_name': None or str,  # None이면 전체, str이면 해당 시나리오
                               'tps': float,
                               'error_rate': float,
                               'vus': int,
                               'avg_response_time': float,
                               'p95_response_time': float,
                               'p99_response_time': float
                           },
                           ...
                       ]
    
    Returns:
        bool: 저장 성공 여부
    """
    try:
        if not timeseries_data:
            logger.warning(f"No timeseries data to save for scenarios")
            return True
            
        # 시나리오 이름으로 시나리오 ID 매핑을 미리 구성
        scenario_mapping = {}
        for scenario in scenario_histories:
            scenario_mapping[scenario.scenario_tag] = scenario.id
        
        # 배치로 저장할 데이터 준비
        timeseries_models = []
        
        for data_point in timeseries_data:
            # 시나리오 ID 결정
            scenario_history_id = None
            if data_point.get('scenario_name'):
                scenario_history_id = scenario_mapping.get(data_point['scenario_name'])
                if scenario_history_id is None:
                    logger.warning(f"Scenario not found for name: {data_point['scenario_name']}")
                    continue
            
            # 시계열 데이터 모델 생성
            timeseries_model = TestMetricsTimeseriesModel(
                scenario_history_id=scenario_history_id,
                test_history_id=scenario.test_history_id,
                timestamp=data_point['timestamp'],
                tps=data_point.get('tps'),
                error_rate=data_point.get('error_rate'),
                vus=data_point.get('vus'),
                avg_response_time=data_point.get('avg_response_time'),
                p95_response_time=data_point.get('p95_response_time'),
                p99_response_time=data_point.get('p99_response_time')
            )
            timeseries_models.append(timeseries_model)
        
        if timeseries_models:
            # 배치 저장
            db.add_all(timeseries_models)
            db.commit()
            
            logger.info(f"Saved {len(timeseries_models)} timeseries data points for scenarios")
        else:
            logger.warning(f"No valid timeseries data to save for scenarios")
        
        return True
        
    except Exception as e:
        logger.error(f"Error saving timeseries metrics: {e}")
        db.rollback()
        return False


def get_test_timeseries_metrics(db: Session, test_history_id: int) -> List[TestMetricsTimeseriesModel]:
    """
    테스트의 시계열 메트릭 데이터 조회
    
    Args:
        db: 데이터베이스 세션
        test_history_id: 테스트 히스토리 ID
    
    Returns:
        시계열 메트릭 데이터 리스트
    """
    try:
        return (
            db.query(TestMetricsTimeseriesModel)
            .filter(TestMetricsTimeseriesModel.test_history_id == test_history_id)
            .order_by(TestMetricsTimeseriesModel.timestamp.asc(), TestMetricsTimeseriesModel.scenario_id.asc())
            .all()
        )
    except Exception as e:
        logger.error(f"Error getting timeseries metrics for test_history_id {test_history_id}: {e}")
        return []


def get_test_timeseries_metrics_by_scenario(db: Session, test_history_id: Optional[int] = None, scenario_history_id: Optional[int] = None) -> List[TestMetricsTimeseriesModel]:
    """
    특정 시나리오의 시계열 메트릭 데이터 조회
    
    Args:
        db: 데이터베이스 세션
        test_history_id: 테스트 히스토리 ID
        scenario_id: 시나리오 ID (None이면 전체 데이터)
    
    Returns:
        시계열 메트릭 데이터 리스트
    """
    try:
        query = db.query(TestMetricsTimeseriesModel).filter(
            TestMetricsTimeseriesModel.test_history_id == test_history_id,
            TestMetricsTimeseriesModel.scenario_history_id == scenario_history_id
        )
        
        return query.order_by(TestMetricsTimeseriesModel.timestamp.asc()).all()
        
    except Exception as e:
        logger.error(f"Error getting timeseries metrics for scenario {scenario_history_id}: {e}")
        return []


def build_test_history_timeseries_response(db: Session, test_history_id: int) -> Optional[TestHistoryTimeseriesResponse]:
    """
    테스트 히스토리의 시계열 데이터를 응답 형식으로 변환
    
    Args:
        db: 데이터베이스 세션
        test_history_id: 테스트 히스토리 ID
    
    Returns:
        시계열 데이터 응답 또는 None
    """
    try:
        # 테스트 히스토리 조회
        test_history = get_test_history_by_id(db, test_history_id)
        if not test_history:
            logger.error(f"Test history not found for id: {test_history_id}")
            return None
        
        # 전체 시계열 데이터 조회 (scenario_id = None)
        overall_timeseries_data = get_test_timeseries_metrics_by_scenario(db, test_history_id, None)
        
        # 전체 데이터를 TimeseriesDataPoint로 변환
        overall_data = [
            TimeseriesDataPoint(
                timestamp=data.timestamp,
                tps=data.tps,
                error_rate=data.error_rate,
                vus=data.vus,
                avg_response_time=data.avg_response_time,
                p95_response_time=data.p95_response_time,
                p99_response_time=data.p99_response_time
            ) for data in overall_timeseries_data
        ]
        
        # 시나리오별 시계열 데이터 구성
        scenarios = []
        for scenario in test_history.scenarios:
            # 해당 시나리오의 시계열 데이터 조회
            scenario_timeseries_data = get_test_timeseries_metrics_by_scenario(db, test_history_id, scenario.id)
            
            # 시계열 데이터를 TimeseriesDataPoint로 변환
            scenario_data = [
                TimeseriesDataPoint(
                    timestamp=data.timestamp,
                    tps=data.tps,
                    error_rate=data.error_rate,
                    vus=data.vus,
                    avg_response_time=data.avg_response_time,
                    p95_response_time=data.p95_response_time,
                    p99_response_time=data.p99_response_time
                ) for data in scenario_timeseries_data
            ]
            
            # endpoint summary 가져오기
            endpoint_summary = None
            if scenario.endpoint:
                endpoint_summary = scenario.endpoint.summary
            
            scenario_response = ScenarioTimeseriesResponse(
                scenario_name=scenario.name,
                endpoint_summary=endpoint_summary,
                data=scenario_data
            )
            scenarios.append(scenario_response)
        
        # 최종 응답 구성
        return TestHistoryTimeseriesResponse(
            overall=OverallTimeseriesResponse(data=overall_data),
            scenarios=scenarios
        )
        
    except Exception as e:
        logger.error(f"Error building timeseries response for test_history_id {test_history_id}: {e}")
        return None


# === 리소스 메트릭 관련 함수들 ===

def save_test_resource_metrics(db: Session, scenario_history: ScenarioHistoryModel, server_infra_id: int, resource_data: List[Dict]) -> bool:
    """
    테스트 완료 후 서버 리소스 메트릭 데이터를 저장 (CPU, Memory)
    
    Args:
        db: 데이터베이스 세션
        scenario_history: 시나리오 히스토리 (해당 서버 인프라와 연결된)
        server_infra_id: 서버 인프라 ID
        resource_data: InfluxDB에서 조회한 리소스 데이터 리스트
                      [
                          {
                              'timestamp': datetime,
                              'metric_type': 'cpu' or 'memory',
                              'unit': 'millicores' or 'mb',
                              'value': float
                          },
                          ...
                      ]
    
    Returns:
        bool: 저장 성공 여부
    """
    try:
        if not resource_data:
            logger.warning(f"No resource data to save for scenarios, server_infra_id: {server_infra_id}")
            return True
            
        # 배치로 저장할 데이터 준비
        resource_models = []
        
        for data_point in resource_data:
            # 리소스 데이터 모델 생성
            resource_model = TestResourceTimeseriesModel(
                scenario_history_id=scenario_history.id,
                server_infra_id=server_infra_id,
                metric_type=data_point['metric_type'],
                unit=data_point['unit'],
                timestamp=data_point['timestamp'],
                value=data_point['value']
            )
            resource_models.append(resource_model)
        
        if resource_models:
            # 배치 저장
            db.add_all(resource_models)
            db.commit()
            
            logger.info(f"Saved {len(resource_models)} resource data points for scenario_id: {scenario_history.id}, server_infra_id: {server_infra_id}")
        else:
            logger.warning(f"No valid resource data to save for scenario_id: {scenario_history.id}, server_infra_id: {server_infra_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error saving resource metrics: {e}")
        db.rollback()
        return False


def get_group_pods_names_by_server_infra_id(db: Session, server_infra_id: int) -> List[str]:
    """
    server_infra_id로 관련된 pod 이름들을 조회
    resource_type이 'pod'가 아닌 경우 group_name으로 같은 deployment/statefulset의 pod들을 찾음
    
    Args:
        db: 데이터베이스 세션
        server_infra_id: 서버 인프라 ID
        
    Returns:
        pod 이름 리스트
    """
    try:
        from app.db.sqlite.models.project_models import ServerInfraModel
        
        # server_infra 조회
        server_infra = db.query(ServerInfraModel).filter(ServerInfraModel.id == server_infra_id).first()
        if not server_infra:
            logger.warning(f"No server_infra found for id: {server_infra_id}")
            return []
            
        pod_names = []
        
        if server_infra.resource_type and server_infra.resource_type.lower() == 'pod':
            # resource_type이 'pod'인 경우 해당 pod 이름 반환
            if server_infra.name:
                pod_names.append(server_infra.name)
        else:
            # resource_type이 'deployment', 'statefulset' 등인 경우 group_name으로 관련 pod들 조회
            if server_infra.group_name:
                logger.debug(f"Looking for related pods with group_name: {server_infra.group_name}")
                group_pods = (
                    db.query(ServerInfraModel)
                    .filter(
                        ServerInfraModel.group_name == server_infra.group_name
                    )
                    .all()
                )
                
                for i, pod in enumerate(group_pods):
                    if pod.name:
                        pod_names.append(pod.name)

        return pod_names

    except Exception as e:
        logger.error(f"Error getting pod names for server_infra_id {server_infra_id}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []


def get_scenario_by_server_infra_id(db: Session, scenario_histories: List[ScenarioHistoryModel], server_infra_id: int) -> Optional[ScenarioHistoryModel]:
    """
    서버 인프라 ID로 연결된 시나리오를 찾는다
    server_infra -> openapi_spec -> endpoint -> scenario
    
    Args:
        db: 데이터베이스 세션
        scenario_histories: 시나리오 히스토리 리스트
        server_infra_id: 서버 인프라 ID
        
    Returns:
        연결된 시나리오 히스토리 또는 None
    """
    try:
        from app.db.sqlite.models.project_models import ServerInfraModel
        
        # server_infra 조회
        server_infra = db.query(ServerInfraModel).filter(ServerInfraModel.id == server_infra_id).first()
        if not server_infra or not server_infra.open_api_spec_id:
            logger.warning(f"No server_infra or openapi_spec_id found for server_infra_id: {server_infra_id}")
            return scenario_histories[0] if scenario_histories else None  # 기본값으로 첫 번째 시나리오 반환
        
        # 해당 openapi_spec_id와 연결된 시나리오 찾기
        for scenario in scenario_histories:
            if scenario.endpoint and scenario.endpoint.tags:
                for tag in scenario.endpoint.tags:
                    if tag.openapi_spec_id == server_infra.open_api_spec_id:
                        logger.info(f"Found matching scenario {scenario.id} for server_infra_id: {server_infra_id}")
                        return scenario
        
        logger.warning(f"No matching scenario found for server_infra_id: {server_infra_id}, using first scenario")
        return scenario_histories[0] if scenario_histories else None  # 매칭되지 않으면 첫 번째 시나리오 반환
        
    except Exception as e:
        logger.error(f"Error finding scenario for server_infra_id {server_infra_id}: {e}")
        return scenario_histories[0] if scenario_histories else None
