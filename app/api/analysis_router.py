from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models import get_db, get_async_db
from app.services.analysis.ai_analysis_service import AIAnalysisService
from app.services.analysis.model_manager import get_model_manager
from app.schemas.analysis import (
    AnalysisType, SingleAnalysisResponse, ComprehensiveAnalysisResponse,
    ComparisonAnalysisResponse, ModelInfoResponse, AnalysisStatusResponse,
    HealthCheckResponse, SingleAnalysisRequest, ComprehensiveAnalysisRequest,
    ComparisonAnalysisRequest, AnalysisHistoryResponse
)
from app.services.testing.test_history_service import get_test_history_by_id


router = APIRouter(prefix="/analysis", tags=["AI Analysis"])


# 백그라운드 작업 상태 저장소 (향후 Redis로 대체)
analysis_status_store: Dict[str, Dict[str, Any]] = {}

# AI 분석은 k6 Job 완료 시 자동으로 실행
# 분석 결과는 GET /history/{test_history_id} 엔드포인트에서 조회


@router.get("/history/{test_history_id}", response_model=AnalysisHistoryResponse)
async def get_analysis_history(
    test_history_id: int,
    limit: int = Query(50, description="조회할 이력 개수 (최대 100개)"),
    analysis_type: Optional[str] = Query(None, description="특정 분석 유형 필터링"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    테스트의 분석 이력 조회

    ## 기능
    - k6 테스트 완료 후 자동으로 실행된 AI 분석 결과들을 조회합니다
    - 모든 분석 유형 (TPS, 응답시간, 에러율, 리소스 사용량, 종합분석) 포함
    - 분석 유형별 필터링 지원

    ## 자동 분석 유형
    - **tps**: 처리량 성능 및 확장성 분석
    - **response_time**: 응답시간 분포 및 안정성 분석
    - **error_rate**: 오류 발생 패턴 및 안정성 분석
    - **resource_usage**: CPU/Memory 효율성 분석
    - **comprehensive**: 전체적인 성능 상황 종합 평가

    ## 파라미터
    - **test_history_id**: 테스트 히스토리 ID
    - **limit**: 조회할 이력 개수 (기본값: 50, 최대: 100)
    - **analysis_type**: 분석 유형 필터 (tps, response_time, error_rate, resource_usage, comprehensive)

    ## 응답
    - 최신 분석부터 시간 순서로 정렬
    - 각 분석의 요약, 분석 유형, 수행 시각 포함
    - 분석 결과는 테스트 완료 후 자동으로 생성

    Returns:
        AI 분석 이력 목록
    """

    try:
        from app.repositories.analysis_history_repository import get_analysis_history_repository

        # 제한값 검증
        limit = min(max(1, limit), 100)

        history_repo = get_analysis_history_repository()

        if analysis_type:
            # 특정 분석 유형 필터링
            analyses = await history_repo.get_analyses_by_type(db, test_history_id, analysis_type, limit)
        else:
            # 모든 분석 이력 조회
            analyses = await history_repo.get_test_analysis_history(db, test_history_id, limit)

        # 응답 데이터 구성
        analysis_items = []
        for analysis in analyses:
            # analysis_type을 AnalysisType enum으로 변환
            analysis_type_enum = None
            try:
                from app.schemas.analysis.analysis_request import AnalysisType
                if analysis.analysis_type in [at.value for at in AnalysisType]:
                    analysis_type_enum = AnalysisType(analysis.analysis_type)
                else:
                    # comparison 등 enum에 없는 경우 기본값 사용
                    analysis_type_enum = AnalysisType.comprehensive
            except:
                analysis_type_enum = AnalysisType.comprehensive

            item = {
                "id": analysis.id,
                "test_history_id": analysis.primary_test_id,  # AnalysisHistoryItem에서 요구하는 필드명
                "analysis_type": analysis_type_enum,
                "model_name": analysis.model_name,
                "analyzed_at": analysis.analyzed_at,
                "summary": _extract_summary_from_result(analysis.analysis_result)
            }
            analysis_items.append(item)

        return AnalysisHistoryResponse(
            test_history_id=test_history_id,
            total_count=len(analysis_items),
            analyses=analysis_items
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analysis history: {str(e)}"
        )


def _extract_summary_from_result(analysis_result: dict) -> str:
    """분석 결과에서 요약 텍스트 추출"""
    if "summary" in analysis_result:
        return analysis_result["summary"]
    elif "comparison_summary" in analysis_result:
        return analysis_result["comparison_summary"]
    else:
        return "분석 요약 정보 없음"


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    AI 분석 서비스 상태 확인
    
    Returns:
        서비스 상태 정보
    """
    
    try:
        ai_service = AIAnalysisService()
        model_manager = get_model_manager()
        
        # Ollama 상태 확인
        from app.services.analysis.ollama_client import get_ollama_client
        ollama_client = await get_ollama_client()
        ollama_health = await ollama_client.health_check()
        
        # 모델 성능 통계
        performance_stats = model_manager.get_performance_stats()
        
        # 사용 가능한 모델 목록
        available_models_data = await model_manager.get_available_models()
        available_models = [m["name"] for m in available_models_data if m["is_available"]]
        
        # 전체 서비스 상태 결정
        overall_status = "healthy"
        if ollama_health["status"] != "healthy":
            overall_status = "degraded" if available_models else "unhealthy"
        
        return HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.now(),
            ollama_status=ollama_health,
            database_status={"status": "healthy"},  # TODO: DB 상태 체크 구현
            available_models=available_models,
            active_analyses=len([s for s in analysis_status_store.values() if s["status"] == "running"]),
            total_analyses_today=performance_stats.get("total_analyses", 0)
        )
        
    except Exception as e:
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            ollama_status={"status": "error", "error": str(e)},
            database_status={"status": "unknown"},
            available_models=[],
            active_analyses=0,
            total_analyses_today=0
        )