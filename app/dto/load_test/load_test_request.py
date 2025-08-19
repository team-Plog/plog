from pydantic import BaseModel
from typing import Optional, List

class StageConfig(BaseModel):
    duration: str = "10s"
    target: int = 10

class ScenarioParameter(BaseModel):
    name: str              # 파라미터 이름
    param_type: str        # "path", "query", "requestBody"
    value: str             # 실제 값 (문자열)

class ScenarioHeader(BaseModel):
    header_key: str        # 헤더 키 (예: "Authorization", "Content-Type")
    header_value: str      # 헤더 값 (예: "Bearer token123", "application/json")

class ScenarioConfig(BaseModel):
    name: str = "제목없음"
    endpoint_id: int = 1
    executor: str = "constant-vus"   # ex: "constant-vus" or "ramping-vus"
    think_time: float = 1.0
    stages: List[StageConfig]
    parameters: Optional[List[ScenarioParameter]] = None  # 파라미터 배열
    headers: Optional[List[ScenarioHeader]] = None        # 헤더 배열
    response_time_target: Optional[float] = None  # 응답시간 목표 (ms)
    error_rate_target: Optional[float] = None     # 에러율 목표 (%)

class LoadTestRequest(BaseModel):
    title: str = "load testing"
    description: str = "설명 없음"
    target_tps: Optional[float] = None  # 공통 목표 TPS
    scenarios: List[ScenarioConfig]
