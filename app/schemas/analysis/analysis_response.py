from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from .analysis_request import AnalysisType
from .analysis_models import AnalysisInsight


class SingleAnalysisResponse(BaseModel):
    """개별 분석 결과 응답"""
    analysis_type: AnalysisType = Field(..., description="분석 유형")
    summary: str = Field(..., description="3-4문장 요약")
    detailed_analysis: str = Field(..., description="상세 분석 내용")
    insights: List[AnalysisInsight] = Field(default=[], description="주요 인사이트")
    performance_score: Optional[float] = Field(None, ge=0, le=100, description="성능 점수 (0-100)")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="분석 신뢰도 (0-1)")
    
    # 메타데이터
    analyzed_at: datetime = Field(..., description="분석 수행 시각")
    model_name: str = Field(..., description="사용된 AI 모델명")
    analysis_duration_ms: Optional[int] = Field(None, description="분석 소요 시간(ms)")


class ComprehensiveAnalysisResponse(BaseModel):
    """종합 분석 응답"""
    test_history_id: int = Field(..., description="테스트 히스토리 ID")
    analyzed_at: datetime = Field(..., description="분석 수행 시각")
    model_name: str = Field(..., description="사용된 AI 모델명")
    
    # 종합 결과
    overall_performance_score: float = Field(..., ge=0, le=100, description="전체 성능 점수")
    executive_summary: str = Field(..., description="경영진용 한줄 요약")
    
    # 세부 분석 결과
    analyses: List[SingleAnalysisResponse] = Field(..., description="세부 분석 결과 목록")
    
    # 우선순위 권장사항
    top_recommendations: List[str] = Field(..., max_items=5, description="상위 권장사항")
    
    # 추세 분석 (비교가 있는 경우)
    trend_analysis: Optional[str] = Field(None, description="이전 테스트 대비 변화")
    
    # 메타데이터
    total_analysis_duration_ms: Optional[int] = Field(None, description="전체 분석 소요 시간(ms)")


class ComparisonAnalysisResponse(BaseModel):
    """비교 분석 응답"""
    current_test_id: int = Field(..., description="현재 테스트 ID")
    previous_test_id: int = Field(..., description="이전 테스트 ID")
    analyzed_at: datetime = Field(..., description="분석 수행 시각")
    model_name: str = Field(..., description="사용된 AI 모델명")
    
    # 비교 요약
    comparison_summary: str = Field(..., description="비교 분석 요약")
    improvement_percentage: Optional[float] = Field(None, description="전반적 개선도 (%)")
    
    # 지표별 비교
    tps_comparison: Optional[Dict[str, float]] = Field(None, description="TPS 비교 (previous, current, change_%)")
    response_time_comparison: Optional[Dict[str, float]] = Field(None, description="응답시간 비교")
    error_rate_comparison: Optional[Dict[str, float]] = Field(None, description="에러율 비교")
    resource_usage_comparison: Optional[Dict[str, float]] = Field(None, description="리소스 사용량 비교")
    
    # 주요 변화 사항
    improvements: List[str] = Field(default=[], description="개선 사항")
    regressions: List[str] = Field(default=[], description="성능 저하 사항")
    
    # 상세 분석
    detailed_comparison: str = Field(..., description="상세 비교 분석")
    insights: List[AnalysisInsight] = Field(default=[], description="비교 분석 인사이트")


class AnalysisHistoryItem(BaseModel):
    """분석 이력 아이템"""
    id: int = Field(..., description="분석 ID")
    test_history_id: int = Field(..., description="테스트 히스토리 ID")
    analysis_type: AnalysisType = Field(..., description="분석 유형")
    model_name: str = Field(..., description="사용된 모델명")
    performance_score: Optional[float] = Field(None, description="성능 점수")
    analyzed_at: datetime = Field(..., description="분석 수행 시각")
    summary: str = Field(..., description="분석 요약")


class AnalysisHistoryResponse(BaseModel):
    """분석 이력 응답"""
    test_history_id: int = Field(..., description="테스트 히스토리 ID")
    total_count: int = Field(..., description="전체 분석 이력 수")
    analyses: List[AnalysisHistoryItem] = Field(..., description="분석 이력 목록")


class ModelInfoResponse(BaseModel):
    """모델 정보 응답"""
    name: str = Field(..., description="모델명")
    provider: str = Field(..., description="제공자")
    display_name: str = Field(..., description="표시명")
    description: str = Field(..., description="모델 설명")
    capabilities: List[str] = Field(..., description="모델 기능")
    max_tokens: int = Field(..., description="최대 토큰 수")
    is_available: bool = Field(..., description="사용 가능 여부")
    performance_score: float = Field(default=0.0, description="성능 점수")


class AnalysisStatusResponse(BaseModel):
    """분석 상태 응답"""
    test_history_id: int = Field(..., description="테스트 히스토리 ID")
    status: str = Field(..., description="상태 (pending, running, completed, failed)")
    progress_percentage: Optional[int] = Field(None, ge=0, le=100, description="진행률")
    current_step: Optional[str] = Field(None, description="현재 수행 중인 단계")
    started_at: Optional[datetime] = Field(None, description="시작 시각")
    completed_at: Optional[datetime] = Field(None, description="완료 시각")
    error_message: Optional[str] = Field(None, description="오류 메시지")
    estimated_completion: Optional[datetime] = Field(None, description="예상 완료 시각")


class HealthCheckResponse(BaseModel):
    """헬스 체크 응답"""
    status: str = Field(..., description="서비스 상태 (healthy, degraded, unhealthy)")
    timestamp: datetime = Field(..., description="체크 시각")
    
    # 컴포넌트별 상태
    ollama_status: Dict[str, Any] = Field(..., description="Ollama 상태")
    database_status: Dict[str, Any] = Field(..., description="데이터베이스 상태")
    
    # 성능 메트릭
    available_models: List[str] = Field(..., description="사용 가능한 모델 목록")
    active_analyses: int = Field(..., description="진행 중인 분석 수")
    total_analyses_today: int = Field(default=0, description="오늘 수행된 분석 수")