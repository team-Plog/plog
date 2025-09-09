# schemas/scenario_history.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ScenarioHistoryCreate(BaseModel):
    """히스토리 생성용 스키마 - 빈 클래스"""
    pass

class ScenarioHistoryUpdate(BaseModel):
    """히스토리 업데이트용 스키마 - 빈 클래스"""
    pass