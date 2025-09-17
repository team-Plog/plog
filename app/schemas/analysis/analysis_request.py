from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class AnalysisType(str, Enum):
    """분석 유형"""
    COMPREHENSIVE = "comprehensive"
    RESPONSE_TIME = "response_time"
    TPS = "tps"
    ERROR_RATE = "error_rate"
    RESOURCE_USAGE = "resource_usage"


class SingleAnalysisRequest(BaseModel):
    """개별 분석 요청"""
    test_history_id: int = Field(..., description="분석할 테스트 히스토리 ID")
    analysis_type: AnalysisType = Field(..., description="수행할 분석 유형")


class ComprehensiveAnalysisRequest(BaseModel):
    """종합 분석 요청"""
    test_history_id: int = Field(..., description="분석할 테스트 히스토리 ID")
    analysis_types: Optional[List[AnalysisType]] = Field(
        None,
        description="수행할 분석 유형 목록 (미지정시 전체 분석)"
    )
    comparison_test_ids: Optional[List[int]] = Field(
        None,
        description="비교 분석용 이전 테스트 ID 목록"
    )
    run_in_background: bool = Field(False, description="백그라운드 실행 여부")


class ComparisonAnalysisRequest(BaseModel):
    """비교 분석 요청"""
    current_test_id: int = Field(..., description="현재 테스트 ID")
    previous_test_id: int = Field(..., description="비교할 이전 테스트 ID")
    focus_areas: Optional[List[str]] = Field(
        None,
        description="집중 분석 영역 (tps, response_time, error_rate, resource_usage)"
    )