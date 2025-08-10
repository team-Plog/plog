from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MetricGroupResponse(BaseModel):
    """메트릭의 최대, 최소, 평균값을 담는 공통 구조"""
    max: Optional[float] = None
    min: Optional[float] = None
    avg: Optional[float] = None


class VusMetricResponse(BaseModel):
    """VUS 메트릭 (정수형)"""
    max: Optional[float] = None
    min: Optional[float] = None
    avg: Optional[float] = None  # 평균은 소수점 가능


class ResponseTimeMetricResponse(BaseModel):
    """응답시간 메트릭 (p50, p95, p99 포함)"""
    max: Optional[float] = None
    min: Optional[float] = None
    avg: Optional[float] = None
    p50: Optional[float] = None
    p95: Optional[float] = None
    p99: Optional[float] = None


class OverallMetricsResponse(BaseModel):
    """전체 테스트 메트릭 구조"""
    target_tps: Optional[float] = None
    total_requests: Optional[int] = None
    failed_requests: Optional[int] = None
    test_duration: Optional[float] = None
    tps: Optional[MetricGroupResponse] = None
    response_time: Optional[ResponseTimeMetricResponse] = None
    error_rate: Optional[MetricGroupResponse] = None
    vus: Optional[VusMetricResponse] = None


class StageHistoryDetailResponse(BaseModel):
    stage_history_id: int
    duration: str
    target: int

    class Config:
        from_attributes = True


class EndpointDetailResponse(BaseModel):
    endpoint_id: int
    method: Optional[str] = None
    path: Optional[str] = None
    description: Optional[str] = None
    summary: Optional[str] = None

    class Config:
        from_attributes = True


class ScenarioHistoryDetailResponse(BaseModel):
    scenario_history_id: int
    name: str
    scenario_tag: str
    total_requests: Optional[int] = None
    failed_requests: Optional[int] = None
    test_duration: Optional[float] = None
    response_time_target: Optional[float] = None
    error_rate_target: Optional[float] = None
    think_time: float
    executor: str
    endpoint: Optional[EndpointDetailResponse] = None
    tps: Optional[MetricGroupResponse] = None
    response_time: Optional[ResponseTimeMetricResponse] = None
    error_rate: Optional[MetricGroupResponse] = None
    stages: List[StageHistoryDetailResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class TestHistoryDetailResponse(BaseModel):
    test_history_id: int
    project_id: int
    title: str
    description: Optional[str] = None
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    tested_at: Optional[datetime] = None
    job_name: Optional[str] = None
    k6_script_file_name: Optional[str] = None

    overall: Optional[OverallMetricsResponse] = None
    scenarios: List[ScenarioHistoryDetailResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True