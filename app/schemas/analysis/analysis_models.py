from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class PerformanceMetrics(BaseModel):
    """성능 메트릭 기본 구조"""
    max_value: Optional[float] = None
    min_value: Optional[float] = None 
    avg_value: Optional[float] = None


class ResponseTimeMetrics(PerformanceMetrics):
    """응답시간 메트릭 (백분위수 포함)"""
    p50: Optional[float] = None
    p95: Optional[float] = None
    p99: Optional[float] = None


class TestConfiguration(BaseModel):
    """테스트 설정 정보"""
    title: str
    description: Optional[str] = None
    target_tps: Optional[float] = None
    test_duration: Optional[float] = None
    total_requests: Optional[int] = None
    failed_requests: Optional[int] = None
    error_rate_percent: Optional[float] = None


class EndpointInfo(BaseModel):
    """엔드포인트 정보"""
    method: Optional[str] = None
    path: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None


class ScenarioMetrics(BaseModel):
    """시나리오별 메트릭"""
    scenario_name: str
    endpoint: Optional[EndpointInfo] = None
    executor: str
    think_time: float
    
    # 성능 지표
    tps: Optional[PerformanceMetrics] = None
    response_time: Optional[ResponseTimeMetrics] = None
    error_rate: Optional[PerformanceMetrics] = None
    vus: Optional[PerformanceMetrics] = None
    
    # 목표 대비 성능
    response_time_target: Optional[float] = None
    error_rate_target: Optional[float] = None
    
    # 실제 결과
    total_requests: Optional[int] = None
    failed_requests: Optional[int] = None
    actual_test_duration: Optional[float] = None


class ResourceUsagePoint(BaseModel):
    """리소스 사용량 데이터 포인트"""
    timestamp: datetime
    cpu_usage_percent: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    cpu_usage_millicores: Optional[float] = None
    memory_usage_mb: Optional[float] = None


class ResourceSpecification(BaseModel):
    """리소스 사양 정보"""
    cpu_request_millicores: Optional[float] = None
    cpu_limit_millicores: Optional[float] = None
    memory_request_mb: Optional[float] = None
    memory_limit_mb: Optional[float] = None


class ServerResourceUsage(BaseModel):
    """서버별 리소스 사용량"""
    pod_name: str
    service_type: str
    resource_spec: Optional[ResourceSpecification] = None
    usage_data: List[ResourceUsagePoint] = []
    
    # 요약 통계
    avg_cpu_percent: Optional[float] = None
    max_cpu_percent: Optional[float] = None
    avg_memory_percent: Optional[float] = None
    max_memory_percent: Optional[float] = None


class LLMAnalysisInput(BaseModel):
    """LLM 분석을 위한 입력 데이터 구조"""
    
    # 기본 정보
    test_history_id: int
    tested_at: datetime
    is_completed: bool
    
    # 테스트 설정
    configuration: TestConfiguration
    
    # 전체 성능 메트릭
    overall_tps: Optional[PerformanceMetrics] = None
    overall_response_time: Optional[ResponseTimeMetrics] = None
    overall_error_rate: Optional[PerformanceMetrics] = None
    overall_vus: Optional[PerformanceMetrics] = None
    
    # 시나리오별 메트릭
    scenarios: List[ScenarioMetrics] = []
    
    # 서버 리소스 사용량
    resource_usage: List[ServerResourceUsage] = []
    
    # 이전 테스트와의 비교 데이터 (선택사항)
    previous_test_comparison: Optional[Dict[str, Any]] = None


class AnalysisInsight(BaseModel):
    """분석 통찰"""
    category: str  # "performance", "reliability", "resource", "optimization"
    message: str
    severity: str  # "info", "warning", "critical"
    recommendation: Optional[str] = None


class AnalysisResult(BaseModel):
    """분석 결과"""
    analysis_type: str
    summary: str = Field(..., description="3-4문장의 요약된 분석")
    detailed_analysis: str = Field(..., description="상세 분석 내용")
    insights: List[AnalysisInsight] = []
    performance_score: Optional[float] = Field(None, ge=0, le=100, description="성능 점수 (0-100)")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="분석 신뢰도 (0-1)")


def convert_test_history_to_llm_input(
    test_history_detail: Dict[str, Any],
    resource_usage_data: List[Dict[str, Any]] = None
) -> LLMAnalysisInput:
    """TestHistoryDetailResponse를 LLMAnalysisInput으로 변환"""
    
    # 기본 정보 추출
    configuration = TestConfiguration(
        title=test_history_detail.get("title", ""),
        description=test_history_detail.get("description"),
        target_tps=test_history_detail.get("overall", {}).get("target_tps"),
        test_duration=test_history_detail.get("overall", {}).get("test_duration"),
        total_requests=test_history_detail.get("overall", {}).get("total_requests"),
        failed_requests=test_history_detail.get("overall", {}).get("failed_requests")
    )
    
    # 전체 메트릭 변환
    overall = test_history_detail.get("overall", {})
    overall_tps = None
    overall_response_time = None
    
    if overall.get("tps"):
        tps_data = overall["tps"]
        overall_tps = PerformanceMetrics(
            max_value=tps_data.get("max"),
            min_value=tps_data.get("min"),
            avg_value=tps_data.get("avg")
        )
    
    if overall.get("response_time"):
        rt_data = overall["response_time"]
        overall_response_time = ResponseTimeMetrics(
            max_value=rt_data.get("max"),
            min_value=rt_data.get("min"),
            avg_value=rt_data.get("avg"),
            p50=rt_data.get("p50"),
            p95=rt_data.get("p95"),
            p99=rt_data.get("p99")
        )
    
    # 시나리오별 메트릭 변환
    scenarios = []
    for scenario_data in test_history_detail.get("scenarios", []):
        endpoint_info = None
        if scenario_data.get("endpoint"):
            ep = scenario_data["endpoint"]
            endpoint_info = EndpointInfo(
                method=ep.get("method"),
                path=ep.get("path"),
                summary=ep.get("summary"),
                description=ep.get("description")
            )
        
        scenario_metrics = ScenarioMetrics(
            scenario_name=scenario_data.get("name", ""),
            endpoint=endpoint_info,
            executor=scenario_data.get("executor", ""),
            think_time=scenario_data.get("think_time", 0.0),
            response_time_target=scenario_data.get("response_time_target"),
            error_rate_target=scenario_data.get("error_rate_target"),
            total_requests=scenario_data.get("total_requests"),
            failed_requests=scenario_data.get("failed_requests"),
            actual_test_duration=scenario_data.get("test_duration")
        )
        scenarios.append(scenario_metrics)
    
    # 리소스 사용량 데이터 변환
    resource_usage = []
    if resource_usage_data:
        for resource_data in resource_usage_data:
            usage_points = []
            for point in resource_data.get("resource_data", []):
                usage_point = ResourceUsagePoint(
                    timestamp=datetime.fromisoformat(point["timestamp"].replace('Z', '+00:00')),
                    cpu_usage_percent=point.get("usage", {}).get("cpu_percent"),
                    memory_usage_percent=point.get("usage", {}).get("memory_percent"),
                    cpu_usage_millicores=point.get("actual_usage", {}).get("cpu_millicores"),
                    memory_usage_mb=point.get("actual_usage", {}).get("memory_mb")
                )
                usage_points.append(usage_point)
            
            server_usage = ServerResourceUsage(
                pod_name=resource_data.get("pod_name", ""),
                service_type=resource_data.get("service_type", ""),
                usage_data=usage_points
            )
            
            # 평균/최대 사용률 계산
            if usage_points:
                cpu_percentages = [p.cpu_usage_percent for p in usage_points if p.cpu_usage_percent is not None]
                memory_percentages = [p.memory_usage_percent for p in usage_points if p.memory_usage_percent is not None]
                
                if cpu_percentages:
                    server_usage.avg_cpu_percent = sum(cpu_percentages) / len(cpu_percentages)
                    server_usage.max_cpu_percent = max(cpu_percentages)
                
                if memory_percentages:
                    server_usage.avg_memory_percent = sum(memory_percentages) / len(memory_percentages)
                    server_usage.max_memory_percent = max(memory_percentages)
            
            resource_usage.append(server_usage)
    
    return LLMAnalysisInput(
        test_history_id=test_history_detail.get("test_history_id", 0),
        tested_at=datetime.fromisoformat(test_history_detail.get("tested_at", datetime.now().isoformat()).replace('Z', '+00:00')),
        is_completed=test_history_detail.get("is_completed", False),
        configuration=configuration,
        overall_tps=overall_tps,
        overall_response_time=overall_response_time,
        scenarios=scenarios,
        resource_usage=resource_usage
    )