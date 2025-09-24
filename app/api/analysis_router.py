import logging
from datetime import datetime
from typing import Optional, Any
from app.schemas.analysis.analysis_request import AnalysisType

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import get_async_db
from app.schemas.analysis import (
    HealthCheckResponse,
    AnalysisHistoryResponse
)
from app.common.response.response_template import ResponseTemplate


router = APIRouter(prefix="/analysis", tags=["AI Analysis"])

logger = logging.getLogger(__name__)


# AI 분석은 k6 Job 완료 시 자동으로 실행
# 분석 결과는 GET /history/{test_history_id} 엔드포인트에서 조회


@router.get("/history/{test_history_id}", response_model=AnalysisHistoryResponse)
async def get_analysis_history(
    test_history_id: int,
    limit: int = Query(50, description="조회할 이력 개수 (최대 100개)"),
    analysis_type: Optional[AnalysisType] = Query(None, description="특정 분석 유형 필터링"),
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
            analyses = await history_repo.get_analyses_by_type(db, test_history_id, analysis_type.value, limit)
        else:
            # 모든 분석 이력 조회
            analyses = await history_repo.get_test_analysis_history(db, test_history_id, limit)

        # 응답 데이터 구성
        analysis_items = []
        for analysis in analyses:
            # analysis_type을 AnalysisType enum으로 변환
            try:
                analysis_type_enum = AnalysisType(analysis.analysis_type)
            except Exception:
                analysis_type_enum = AnalysisType.COMPREHENSIVE

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

    except ValueError as e:
        logger.error(f"Invalid parameter for analysis history: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid parameter: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving analysis history: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve analysis history due to internal server error"
        )


def _extract_summary_from_result(analysis_result: Any) -> str:
    """분석 결과에서 요약 텍스트 추출 (견고한 처리)"""
    default_summary = "분석 요약 정보 없음"

    if not analysis_result:
        return default_summary

    try:
        # dict 타입인 경우
        if isinstance(analysis_result, dict):
            summary = analysis_result.get("detailed_analysis", "").strip()
            return summary if summary else default_summary

        # string 타입인 경우 (JSON일 가능성)
        if isinstance(analysis_result, str):
            analysis_result = analysis_result.strip()
            if not analysis_result:
                return default_summary

            try:
                import json
                parsed_obj = json.loads(analysis_result)
                if isinstance(parsed_obj, dict):
                    summary = parsed_obj.get("summary", "").strip()
                    return summary if summary else default_summary
            except (json.JSONDecodeError, ValueError):
                # JSON 파싱 실패 시 원본 문자열의 일부를 요약으로 사용
                if len(analysis_result) > 100:
                    return analysis_result[:97] + "..."
                return analysis_result

        # 기타 타입인 경우 문자열로 변환 시도
        summary_str = str(analysis_result).strip()
        if len(summary_str) > 100:
            return summary_str[:97] + "..."
        return summary_str if summary_str else default_summary

    except Exception as e:
        logger.warning(f"Error extracting summary from analysis result: {e}")
        return default_summary


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    AI 분석 서비스 상태 확인
    
    Returns:
        서비스 상태 정보
    """
    
    try:
        # Ollama 상태 확인
        ollama_health = {"status": "unknown"}
        available_models = []

        try:
            from app.services.analysis.ollama_client import get_ollama_client, OllamaConfig
            config = OllamaConfig.from_settings()
            ollama_client = await get_ollama_client(config)
            ollama_health = await ollama_client.health_check()

            # 사용 가능한 모델 목록 확인
            if ollama_health.get("status") == "healthy":
                try:
                    from app.core.config import settings
                    if settings.validate_ai_config():
                        ai_config = settings.get_ai_config()
                        model_name = ai_config.get('model_name')
                        if model_name:
                            available_models = [model_name]
                except Exception as model_error:
                    logger.warning(f"Failed to get model configuration: {model_error}")
                    ollama_health["model_config_error"] = str(model_error)

        except Exception as ollama_error:
            logger.error(f"Ollama health check failed: {ollama_error}")
            ollama_health = {"status": "error", "error": str(ollama_error)}

        # 데이터베이스 상태 확인 (기본값)
        database_status = {"status": "healthy"}  # TODO: 실제 DB 상태 체크 구현

        # 전체 서비스 상태 결정
        overall_status = "healthy"

        if ollama_health.get("status") != "healthy":
            if available_models:
                overall_status = "degraded"
            else:
                overall_status = "unhealthy"

        if database_status.get("status") != "healthy":
            overall_status = "unhealthy"

        return HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.now(),
            ollama_status=ollama_health,
            database_status=database_status,
            available_models=available_models
        )

    except Exception as e:
        logger.error(f"Health check failed with unexpected error: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            ollama_status={"status": "error", "error": str(e)},
            database_status={"status": "unknown"},
            available_models=[]
        )