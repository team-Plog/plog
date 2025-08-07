from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class StageHistoryDetailResponse(BaseModel):
    id: int
    duration: str
    target: int

    class Config:
        from_attributes = True


class EndpointDetailResponse(BaseModel):
    id: int
    path: Optional[str] = None
    method: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


class ScenarioHistoryDetailResponse(BaseModel):
    id: int
    name: str
    endpoint_id: int
    endpoint: Optional[EndpointDetailResponse] = None
    executor: str
    think_time: float
    response_time_target: Optional[float] = None
    error_rate_target: Optional[float] = None
    scenario_name: str
    
    # 메트릭 정보
    actual_tps: Optional[float] = None
    avg_response_time: Optional[float] = None
    max_response_time: Optional[float] = None
    min_response_time: Optional[float] = None
    p95_response_time: Optional[float] = None
    error_rate: Optional[float] = None
    total_requests: Optional[int] = None
    failed_requests: Optional[int] = None
    
    # 스테이지 정보
    stages: List[StageHistoryDetailResponse] = []

    class Config:
        from_attributes = True


class TestHistoryDetailResponse(BaseModel):
    test_history_id: int = Field(alias="id")
    title: str
    description: Optional[str] = None
    target_tps: Optional[float] = None
    tested_at: datetime
    job_name: Optional[str] = None
    k6_script_file_name: Optional[str] = None
    
    # 완료 상태 정보
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    
    # 프로젝트 정보
    project_id: int
    
    # 전체 테스트 메트릭
    actual_tps: Optional[float] = None
    avg_response_time: Optional[float] = None
    max_response_time: Optional[float] = None
    min_response_time: Optional[float] = None
    p95_response_time: Optional[float] = None
    error_rate: Optional[float] = None
    total_requests: Optional[int] = None
    failed_requests: Optional[int] = None
    max_vus: Optional[int] = None
    test_duration: Optional[float] = None
    
    # 시나리오 정보 (엔드포인트, 스테이지 포함)
    scenarios: List[ScenarioHistoryDetailResponse] = []

    class Config:
        from_attributes = True