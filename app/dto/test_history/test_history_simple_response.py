from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TestHistorySimpleResponse(BaseModel):
    project_title: str
    test_title: str
    status_datetime: datetime
    test_status: str

    class Config:
        from_attributes = True