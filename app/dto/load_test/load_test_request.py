from pydantic import BaseModel
from typing import Optional, List

class StageConfig(BaseModel):
    duration: str = "10s"
    target: int = 10

class ScenarioConfig(BaseModel):
    name: str = "scenario"
    endpoint_id: int = 1
    executor: str = "constant-vus"   # ex: "constant-vus" or "ramping-vus"
    think_time: float = 1.0
    stages: List[StageConfig]
    response_time_target: Optional[float] = None  # 응답시간 목표 (ms)
    error_rate_target: Optional[float] = None     # 에러율 목표 (%)

class LoadTestRequest(BaseModel):
    title: str = "load testing"
    description: str = "설명 없음"
    target_tps: Optional[float] = None  # 공통 목표 TPS
    scenarios: List[ScenarioConfig]
