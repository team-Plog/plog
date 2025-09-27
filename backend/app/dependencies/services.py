from functools import lru_cache

from app.common.exception.api_exception import ApiException
from app.common.response.code import BaseCode, FailureCode
from app.services.testing.resource_response_builder import TestHistoryResourcesResponseBuilder
from app.services.testing.resource_summary_response_builder import SummaryResourcesResponseBuilder
from app.services.testing.resource_timeseries_response_builder import TimeseriesResourcesResponseBuilder
from k8s.resource_service import ResourceService
from app.dependencies.repositories import (
    get_test_history_repository,
    get_scenario_history_repository,
    get_test_resource_timeseries_repository
)

@lru_cache()
def get_resource_service() -> ResourceService:
    return ResourceService()

@lru_cache()
def get_resource_response_builder(type: str) -> TestHistoryResourcesResponseBuilder:
    """Spring Bean Container 스타일의 Dependency Injection Factory"""
    
    # 공통 Dependencies 준비
    test_history_repository = get_test_history_repository()
    scenario_history_repository = get_scenario_history_repository()
    test_resource_timeseries_repository = get_test_resource_timeseries_repository()
    resource_service = get_resource_service()
    
    # Constructor Injection으로 빌더 생성
    if type == "timeseries":
        return TimeseriesResourcesResponseBuilder(
            test_history_repository=test_history_repository,
            scenario_history_repository=scenario_history_repository,
            test_resource_timeseries_repository=test_resource_timeseries_repository,
            resource_service=resource_service
        )

    if type == "summary":
        return SummaryResourcesResponseBuilder(
            test_history_repository=test_history_repository,
            scenario_history_repository=scenario_history_repository,
            test_resource_timeseries_repository=test_resource_timeseries_repository,
            resource_service=resource_service
        )

    if type is None:
        raise ApiException(FailureCode.INTERNAL_SERVER_ERROR, "Response Builder Factory: Type is None")

    raise ApiException(FailureCode.INTERNAL_SERVER_ERROR, f"Unknown resource type: {type}")