from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload

from app.db.sqlite.models.history_models import TestHistoryModel, ScenarioHistoryModel, StageHistoryModel
from app.dto.load_test.load_test_request import LoadTestRequest


def save_test_history(
    request: LoadTestRequest,
    k6_script_file_name: str,
    job_name: str,
    db: Session,
):
    # 1. TestHistory 생성
    test_history = TestHistoryModel(
        title=request.title,
        description=request.description,
        target_tps=request.target_tps,
        tested_at=datetime.utcnow(),
        job_name=job_name,
        k6_script_file_name=k6_script_file_name,
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
