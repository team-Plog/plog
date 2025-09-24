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

    # 메타데이터
    analyzed_at: datetime = Field(..., description="분석 수행 시각")
    model_name: str = Field(..., description="사용된 AI 모델명")


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

    # 기본 정보
    available_models: List[str] = Field(..., description="사용 가능한 모델 목록")