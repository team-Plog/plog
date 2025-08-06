import pytz
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload

from app.db.sqlite.models.history_models import TestHistoryModel, ScenarioHistoryModel, StageHistoryModel
from app.db.sqlite.models.project_models import ProjectModel, OpenAPISpecModel, TagModel, EndpointModel, tags_endpoints
from app.dto.load_test.load_test_request import LoadTestRequest
from app.services.project_service import get_project_by_endpoint_id_simple

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
            endpoint_id=scenario.endpoint_id,
            executor=scenario.executor,
            think_time=scenario.think_time,
            response_time_target=scenario.response_time_target,
            error_rate_target=scenario.error_rate_target,
            scenario_name=f'{job_name}#{scenario.endpoint_id}'
        )

        for stage in scenario.stages:
            stage_model = StageHistoryModel(
                duration=stage.duration,
                target=stage.target
            )
            scenario_model.stages.append(stage_model)

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
            .joinedload(ScenarioHistoryModel.endpoint)
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
            .joinedload(ScenarioHistoryModel.endpoint)
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
            .joinedload(ScenarioHistoryModel.endpoint)
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
        
        # 전체 테스트 메트릭 업데이트
        test_history.is_completed = True
        test_history.completed_at = datetime.utcnow()
        test_history.actual_tps = overall_metrics.get('actual_tps', 0.0)
        test_history.avg_response_time = overall_metrics.get('avg_response_time', 0.0)
        test_history.max_response_time = overall_metrics.get('max_response_time', 0.0)
        test_history.min_response_time = overall_metrics.get('min_response_time', 0.0)
        test_history.p95_response_time = overall_metrics.get('p95_response_time', 0.0)
        test_history.error_rate = overall_metrics.get('error_rate', 0.0)
        test_history.total_requests = overall_metrics.get('total_requests', 0)
        test_history.failed_requests = overall_metrics.get('failed_requests', 0)
        test_history.max_vus = overall_metrics.get('max_vus', 0)
        test_history.test_duration = overall_metrics.get('test_duration', 0.0)
        
        # 시나리오별 메트릭 업데이트
        if scenario_metrics:
            for scenario in test_history.scenarios:
                scenario_key = scenario.scenario_name
                if scenario_key in scenario_metrics:
                    metrics = scenario_metrics[scenario_key]
                    scenario.actual_tps = metrics.get('actual_tps', 0.0)
                    scenario.avg_response_time = metrics.get('avg_response_time', 0.0)
                    scenario.max_response_time = metrics.get('max_response_time', 0.0)
                    scenario.min_response_time = metrics.get('min_response_time', 0.0)
                    scenario.p95_response_time = metrics.get('p95_response_time', 0.0)
                    scenario.error_rate = metrics.get('error_rate', 0.0)
                    scenario.total_requests = metrics.get('total_requests', 0)
                    scenario.failed_requests = metrics.get('failed_requests', 0)
        
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
        .offset(page * size) \
        .limit(size) \
        .all()


# === 스케줄러용 추가 함수들 ===

def get_scenario_histories_by_test_id(db: Session, test_id: int) -> List[ScenarioHistoryModel]:
    """test_id로 관련 scenario_history들 조회 (여러 개 가능)"""
    return (
        db.query(ScenarioHistoryModel)
        .filter(ScenarioHistoryModel.test_history_id == test_id)
        .all()
    )


def update_test_history_with_metrics(db: Session, test_history: TestHistoryModel, metrics: Dict[str, Any]) -> bool:
    """test_history에 메트릭 업데이트"""
    try:
        test_history.actual_tps = metrics.get('actual_tps', 0.0)
        test_history.avg_response_time = metrics.get('avg_response_time', 0.0)
        test_history.max_response_time = metrics.get('max_response_time', 0.0)
        test_history.min_response_time = metrics.get('min_response_time', 0.0)
        test_history.p95_response_time = metrics.get('p95_response_time', 0.0)
        test_history.error_rate = metrics.get('error_rate', 0.0)
        test_history.total_requests = metrics.get('total_requests', 0)
        test_history.failed_requests = metrics.get('failed_requests', 0)
        test_history.max_vus = metrics.get('max_vus', 0)
        test_history.test_duration = metrics.get('test_duration', 0.0)
        
        db.commit()
        db.refresh(test_history)
        
        logger.info(f"Updated test_history metrics for job: {test_history.job_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating test_history metrics: {e}")
        db.rollback()
        return False


def update_scenario_history_with_metrics(db: Session, scenario_history: ScenarioHistoryModel, metrics: Dict[str, Any]) -> bool:
    """scenario_history에 메트릭 업데이트"""
    try:
        scenario_history.actual_tps = metrics.get('tps', 0.0)  # 키가 'tps'임에 주의
        scenario_history.avg_response_time = metrics.get('avg_response_time', 0.0)
        scenario_history.max_response_time = metrics.get('max_response_time', 0.0)
        scenario_history.min_response_time = metrics.get('min_response_time', 0.0)
        scenario_history.error_rate = metrics.get('error_rate', 0.0)
        scenario_history.total_requests = metrics.get('total_requests', 0)
        scenario_history.failed_requests = metrics.get('failed_requests', 0)
        
        db.commit()
        db.refresh(scenario_history)
        
        logger.info(f"Updated scenario_history metrics for endpoint_id: {scenario_history.endpoint_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating scenario_history metrics: {e}")
        db.rollback()
        return False


def mark_test_as_completed(db: Session, test_history: TestHistoryModel) -> bool:
    """테스트를 완료 상태로 마킹"""
    try:
        test_history.is_completed = True
        test_history.completed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(test_history)
        
        logger.info(f"Marked test as completed for job: {test_history.job_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error marking test as completed: {e}")
        db.rollback()
        return False
