from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class TimeseriesDataPoint(BaseModel):
    """시계열 데이터 포인트"""
    timestamp: datetime
    tps: Optional[float]
    error_rate: Optional[float]
    vus: Optional[int]
    avg_response_time: Optional[float]
    p95_response_time: Optional[float]
    p99_response_time: Optional[float]

class OverallTimeseriesResponse(BaseModel):
    """전체 시계열 데이터 응답"""
    data: List[TimeseriesDataPoint]

class ScenarioTimeseriesResponse(BaseModel):
    """시나리오별 시계열 데이터 응답"""
    scenario_name: str
    endpoint_summary: Optional[str]
    data: List[TimeseriesDataPoint]

class TestHistoryTimeseriesResponse(BaseModel):
    """테스트 히스토리 시계열 데이터 응답"""
    overall: OverallTimeseriesResponse
    scenarios: List[ScenarioTimeseriesResponse]