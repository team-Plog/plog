from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .base_repository import BaseRepository
from app.models.sqlite.models.history_models import ScenarioHistoryModel
from ..schemas.test_history.scenario_history import ScenarioHistoryCreate, ScenarioHistoryUpdate

class ScenarioHistoryRepository(BaseRepository[ScenarioHistoryModel, ScenarioHistoryCreate, ScenarioHistoryUpdate]):
    def __init__(self):
        """ScenarioHistory 전용 Repository"""
        super().__init__(ScenarioHistoryModel)
    
    async def get_scenario_histories_by_test_history_id(self, db: AsyncSession, test_history_id: int) -> List[ScenarioHistoryModel]:
        """test_history_id로 해당 테스트의 모든 시나리오 히스토리 조회"""
        stmt = select(ScenarioHistoryModel).where(ScenarioHistoryModel.test_history_id == test_history_id)
        result = await db.execute(stmt)
        return result.scalars().all()