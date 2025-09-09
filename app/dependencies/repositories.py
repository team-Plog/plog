from functools import lru_cache
from app.repositories.scenario_history_repository import ScenarioHistoryRepository
from app.repositories.test_history_repository import TestHistoryRepository


@lru_cache()
def get_scenario_history_repository() -> ScenarioHistoryRepository:
    """ScenarioHistoryRepository 싱글턴 인스턴스 반환"""
    return ScenarioHistoryRepository()

@lru_cache()
def get_test_history_repository() -> TestHistoryRepository:
    return TestHistoryRepository()