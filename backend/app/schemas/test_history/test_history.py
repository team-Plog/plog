# schemas/test_history.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TestHistoryCreate(BaseModel):
    """히스토리 생성용 스키마 - 빈 클래스"""
    pass

class TestHistoryUpdate(BaseModel):
    """히스토리 업데이트용 스키마 - 빈 클래스"""
    pass