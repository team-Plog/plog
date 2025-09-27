from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class StageHistoryResponse(BaseModel):
    id: int
    duration: str
    target: int

    class Config:
        from_attributes = True


class EndpointResponse(BaseModel):
    id: int
    path: Optional[str]
    method: Optional[str]
    summary: Optional[str]
    description: Optional[str]

    class Config:
        from_attributes = True


class ScenarioHistoryResponse(BaseModel):
    id: int
    name: str
    endpoint_id: int
    endpoint: Optional[EndpointResponse]
    executor: str
    think_time: float
    response_time_target: Optional[float]
    error_rate_target: Optional[float]
    scenario_name: str
    stages: List[StageHistoryResponse]

    class Config:
        from_attributes = True


class TestHistoryResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    target_tps: Optional[float]
    tested_at: datetime
    job_name: Optional[str]
    k6_script_file_name: Optional[str]
    scenarios: List[ScenarioHistoryResponse]

    class Config:
        from_attributes = True