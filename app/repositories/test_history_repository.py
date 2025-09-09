from app.models.sqlite.models import TestHistoryModel
from app.repositories.base_repository import BaseRepository
from app.schemas.test_history.test_history import TestHistoryCreate, TestHistoryUpdate


class TestHistoryRepository(BaseRepository[TestHistoryModel, TestHistoryCreate, TestHistoryUpdate]):
    def __init__(self):
        super().__init__(TestHistoryModel)

