from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List
import logging

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sqlite.models import TestHistoryModel, ScenarioHistoryModel, TestResourceTimeseriesModel
from app.repositories.scenario_history_repository import ScenarioHistoryRepository
from app.repositories.test_history_repository import TestHistoryRepository
from app.repositories.test_resource_timeseries_repository import TestResourceTimeseriesRepository
from app.services.infrastructure.server_infra_service import get_job_pods_with_service_types_async
from k8s.resource_service import ResourceService

logger = logging.getLogger(__name__)


@dataclass
class ResourceProcessingContext:
    """리소스 처리 컨텍스트"""
    pod_info_list: List[Dict]
    resource_timeseries: List[TestResourceTimeseriesModel]

class TestHistoryResourcesResponseBuilder(ABC):
    """Template Method Pattern을 구현한 리소스 응답 빌더"""
    
    def __init__(
        self,
        test_history_repository: TestHistoryRepository,
        scenario_history_repository: ScenarioHistoryRepository,
        test_resource_timeseries_repository: TestResourceTimeseriesRepository,
        resource_service: ResourceService
    ):
        """Constructor Dependency Injection - Spring Bean Container 스타일"""
        self.test_history_repository = test_history_repository
        self.scenario_history_repository = scenario_history_repository
        self.test_resource_timeseries_repository = test_resource_timeseries_repository
        self.resource_service = resource_service

    async def build_response(
            self,
            db: AsyncSession,
            test_history_id: int
    ) -> List[Dict[str, Any]]:
        """Template Method - 공통 로직을 정의하는 알고리즘 골격"""

        test_history = await self.test_history_repository.get(db, test_history_id)

        if test_history is None:
            logger.error(f"Test history not found for id: {test_history_id}")
            raise HTTPException(status_code=404, detail=f"Test history not found for id: {test_history_id}")

        logger.info(f"Found test_history: {test_history.id}, job_name: {test_history.job_name}")
        job_name = test_history.job_name

        # 시나리오 정보 조회
        scenario_histories = await self.scenario_history_repository.get_scenario_histories_by_test_history_id(db,
                                                                                                         test_history_id)
        scenario_history_ids = [scenario_history.id for scenario_history in scenario_histories]

        pod_info_list = await get_job_pods_with_service_types_async(db, job_name)
        resource_timeseries = await self.test_resource_timeseries_repository.findAllByScenarioHistoryIdsWithServerInfra(db,
                                                                                                                   scenario_history_ids)

        context = ResourceProcessingContext(
            pod_info_list = pod_info_list,
            resource_timeseries = resource_timeseries,
        )

        response = await self._build_final_response(context)
        return response

    @abstractmethod
    async def _build_final_response(self, context: ResourceProcessingContext) -> List[Dict[str, Any]]:
        """구체적인 응답 형식 구성 - 각 구현체에서 정의"""
        pass