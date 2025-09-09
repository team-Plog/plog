from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.sqlite.models import TestResourceTimeseriesModel
from app.models.sqlite.models.project_models import ServerInfraModel
from app.repositories.base_repository import BaseRepository
from app.schemas.test_history.test_resource_timeseries import TestResourceTimeseriesCreate, TestResourceTimeseriesUpdate


class TestResourceTimeseriesRepository(BaseRepository[TestResourceTimeseriesModel, TestResourceTimeseriesCreate, TestResourceTimeseriesUpdate]):
    def __init__(self):
        super().__init__(TestResourceTimeseriesModel)

    async def findAllByScenarioHistoryIds(self, db: AsyncSession, scenario_history_ids):
        stmt = select(TestResourceTimeseriesModel).where(TestResourceTimeseriesModel.server_infra_id.in_(scenario_history_ids))
        result = await db.execute(stmt)
        return result.scalars().all()

    async def findAllByScenarioHistoryIdsWithServerInfra(self, db: AsyncSession, scenario_history_ids):
        stmt = (
            select(TestResourceTimeseriesModel)
            .options(selectinload(TestResourceTimeseriesModel.server_infra))
            .where(TestResourceTimeseriesModel.scenario_history_id.in_(scenario_history_ids))
        )
        result = await db.execute(stmt)
        return result.scalars().all()