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

class LoadTestRequest(BaseModel):
    title: str = "load testing"
    description: str = "설명 없음"
    scenarios: List[ScenarioConfig]
