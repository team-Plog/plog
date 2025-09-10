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


router = APIRouter(prefix="/api/analysis", tags=["AI Performance Analysis"])


# 백그라운드 작업 상태 저장소 (향후 Redis로 대체)
analysis_status_store: Dict[str, Dict[str, Any]] = {}


@router.get("/models", response_model=List[ModelInfoResponse])
async def get_available_models():
    """
    사용 가능한 AI 모델 목록 조회
    
    Returns:
        사용 가능한 모델 정보 목록
    """
    
    try:
        model_manager = get_model_manager()
        models = await model_manager.get_available_models()
        
        return [
            ModelInfoResponse(
                name=model["name"],
                provider=model["provider"],
                display_name=model["display_name"],
                description=model["description"],
                capabilities=model["capabilities"],
                max_tokens=model["max_tokens"],
                is_available=model["is_available"],
                performance_score=model["performance_score"]
            )
            for model in models
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get model list: {str(e)}")


@router.get("/types")
async def get_analysis_types():
    """
    지원하는 분석 유형 목록
    
    Returns:
        분석 유형 목록과 설명
    """
    
    analysis_descriptions = {
        AnalysisType.COMPREHENSIVE: "종합 분석 - 전체적인 성능 상황 종합 평가",
        AnalysisType.RESPONSE_TIME: "응답시간 분석 - 응답시간 분포 및 안정성 상세 분석",
        AnalysisType.TPS: "TPS 분석 - 처리량 성능 및 확장성 상세 분석",
        AnalysisType.ERROR_RATE: "에러율 분석 - 오류 발생 패턴 및 안정성 상세 분석",
        AnalysisType.RESOURCE_USAGE: "자원 사용량 분석 - CPU/Memory 효율성 상세 분석"
    }
    
    return {
        "supported_types": [
            {
                "type": analysis_type.value,
                "name": analysis_type.value.replace("_", " ").title(),
                "description": analysis_descriptions[analysis_type]
            }
            for analysis_type in AnalysisType
        ]
    }


@router.post("/single", response_model=SingleAnalysisResponse)
async def perform_single_analysis(
    request: SingleAnalysisRequest,
    db_sync: Session = Depends(get_db),
    db_async: AsyncSession = Depends(get_async_db)
):
    """
    개별 분석 수행
    
    - **test_history_id**: 분석할 테스트 히스토리 ID
    - **analysis_type**: 수행할 분석 유형
    - **model_name**: 사용할 모델명 (미지정시 자동 선택)
    - **priority**: 분석 우선순위 (speed, quality, balanced)
    
    Returns:
        개별 분석 결과
    """
    
    # 테스트 히스토리 존재 확인
    test_history = get_test_history_by_id(db_sync, request.test_history_id)
    if not test_history:
        raise HTTPException(
            status_code=404,
            detail=f"Test history not found: {request.test_history_id}"
        )
    
    # 완료된 테스트인지 확인
    if not test_history.is_completed:
        raise HTTPException(
            status_code=400,
            detail="Cannot analyze incomplete test. Please wait for test completion."
        )
    
    try:
        ai_service = AIAnalysisService()
        result = await ai_service.perform_single_analysis(
            db_sync=db_sync,
            db_async=db_async,
            test_history_id=request.test_history_id,
            analysis_type=request.analysis_type,
            model_name=request.model_name,
            priority=request.priority
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.post("/comprehensive", response_model=ComprehensiveAnalysisResponse)
async def perform_comprehensive_analysis(
    request: ComprehensiveAnalysisRequest,
    background_tasks: BackgroundTasks,
    db_sync: Session = Depends(get_db),
    db_async: AsyncSession = Depends(get_async_db)
):
    """
    종합 분석 수행
    
    - **test_history_id**: 분석할 테스트 히스토리 ID
    - **analysis_types**: 수행할 분석 유형 목록 (미지정시 전체 분석)
    - **model_name**: 사용할 모델명 (미지정시 자동 선택)
    - **priority**: 분석 우선순위 (speed, quality, balanced)
    - **comparison_test_ids**: 비교 분석용 이전 테스트 ID 목록
    - **run_in_background**: 백그라운드 실행 여부
    
    Returns:
        종합 분석 결과 또는 백그라운드 작업 상태
    """
    
    # 테스트 히스토리 존재 확인
    test_history = get_test_history_by_id(db_sync, request.test_history_id)
    if not test_history:
        raise HTTPException(
            status_code=404,
            detail=f"Test history not found: {request.test_history_id}"
        )
    
    if not test_history.is_completed:
        raise HTTPException(
            status_code=400,
            detail="Cannot analyze incomplete test"
        )
    
    ai_service = EnhancedAIAnalysisService()
    
    if request.run_in_background:
        # 백그라운드 실행
        task_id = f"comprehensive_{request.test_history_id}_{int(datetime.now().timestamp())}"
        analysis_status_store[task_id] = {
            "test_history_id": request.test_history_id,
            "status": "pending",
            "progress_percentage": 0,
            "current_step": "Initializing analysis",
            "started_at": datetime.now(),
            "completed_at": None,
            "error_message": None
        }
        
        background_tasks.add_task(
            _run_background_comprehensive_analysis,
            task_id,
            ai_service,
            db_sync,
            db_async,
            request
        )
        
        return {"message": "Comprehensive analysis started in background", "task_id": task_id}
    
    else:
        # 동기 실행
        try:
            result = await ai_service.perform_comprehensive_analysis(
                db_sync=db_sync,
                db_async=db_async,
                test_history_id=request.test_history_id,
                analysis_types=request.analysis_types,
                model_name=request.model_name,
                priority=request.priority,
                comparison_test_ids=request.comparison_test_ids
            )
            
            return result
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Comprehensive analysis failed: {str(e)}"
            )


@router.post("/compare", response_model=ComparisonAnalysisResponse)
async def perform_comparison_analysis(
    request: ComparisonAnalysisRequest,
    db_sync: Session = Depends(get_db),
    db_async: AsyncSession = Depends(get_async_db)
):
    """
    비교 분석 수행 - 현재 테스트와 이전 테스트 비교
    
    - **current_test_id**: 현재 테스트 ID (분석 대상)
    - **previous_test_id**: 비교할 이전 테스트 ID
    - **focus_areas**: 집중 분석 영역 (tps, response_time, error_rate, resource_usage)
    - **model_name**: 사용할 모델명 (미지정시 자동 선택)
    - **priority**: 분석 우선순위 (speed, quality, balanced)
    
    Returns:
        비교 분석 결과
    """
    
    # 양쪽 테스트 히스토리 존재 확인
    current_test = get_test_history_by_id(db_sync, request.current_test_id)
    if not current_test:
        raise HTTPException(
            status_code=404,
            detail=f"Current test not found: {request.current_test_id}"
        )
    
    previous_test = get_test_history_by_id(db_sync, request.previous_test_id)
    if not previous_test:
        raise HTTPException(
            status_code=404,
            detail=f"Previous test not found: {request.previous_test_id}"
        )
    
    # 완료된 테스트인지 확인
    if not current_test.is_completed:
        raise HTTPException(
            status_code=400,
            detail="Cannot analyze incomplete current test"
        )
    
    if not previous_test.is_completed:
        raise HTTPException(
            status_code=400,
            detail="Cannot compare with incomplete previous test"
        )
    
    try:
        ai_service = AIAnalysisService()
        result = await ai_service.perform_comparison_analysis(
            db_sync=db_sync,
            db_async=db_async,
            current_test_id=request.current_test_id,
            previous_test_id=request.previous_test_id,
            focus_areas=request.focus_areas,
            model_name=request.model_name,
            priority=request.priority
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Comparison analysis failed: {str(e)}"
        )


@router.get("/compare/latest/{test_history_id}", response_model=ComparisonAnalysisResponse)
async def compare_with_latest_test(
    test_history_id: int,
    focus_areas: Optional[List[str]] = Query(None, description="집중 분석 영역"),
    model_name: Optional[str] = Query(None, description="사용할 모델명"),
    priority: str = Query("balanced", description="분석 우선순위"),
    db_sync: Session = Depends(get_db),
    db_async: AsyncSession = Depends(get_async_db)
):
    """
    해당 프로젝트의 직전 테스트와 비교 분석
    
    - **test_history_id**: 현재 테스트 ID
    - **focus_areas**: 집중 분석 영역 (쿼리 파라미터)
    - **model_name**: 사용할 모델명 (쿼리 파라미터)
    - **priority**: 분석 우선순위 (쿼리 파라미터)
    
    Returns:
        직전 테스트와의 비교 분석 결과
    """
    
    # 현재 테스트 확인
    current_test = get_test_history_by_id(db_sync, test_history_id)
    if not current_test:
        raise HTTPException(
            status_code=404,
            detail=f"Test not found: {test_history_id}"
        )
    
    if not current_test.is_completed:
        raise HTTPException(
            status_code=400,
            detail="Cannot analyze incomplete test"
        )
    
    # 같은 프로젝트의 이전 테스트 찾기
    from app.services.testing.test_history_service import get_test_histories_by_project_id
    
    project_tests = get_test_histories_by_project_id(db_sync, current_test.project_id)
    
    # 완료된 테스트들만 필터링하고 현재 테스트 이전의 테스트들로 제한
    completed_tests = [
        t for t in project_tests 
        if t.is_completed and t.id != test_history_id and t.tested_at < current_test.tested_at
    ]
    
    if not completed_tests:
        raise HTTPException(
            status_code=404,
            detail="No previous completed test found for comparison"
        )
    
    # 가장 최근 테스트 선택
    latest_previous_test = max(completed_tests, key=lambda t: t.tested_at)
    
    try:
        ai_service = AIAnalysisService()
        result = await ai_service.perform_comparison_analysis(
            db_sync=db_sync,
            db_async=db_async,
            current_test_id=test_history_id,
            previous_test_id=latest_previous_test.id,
            focus_areas=focus_areas,
            model_name=model_name,
            priority=priority
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Comparison analysis failed: {str(e)}"
        )


@router.get("/status/{task_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(task_id: str):
    """
    백그라운드 분석 작업 상태 조회
    
    - **task_id**: 작업 ID
    
    Returns:
        분석 작업 상태 정보
    """
    
    if task_id not in analysis_status_store:
        raise HTTPException(
            status_code=404,
            detail="Analysis task not found"
        )
    
    status_data = analysis_status_store[task_id]
    
    return AnalysisStatusResponse(
        test_history_id=status_data["test_history_id"],
        status=status_data["status"],
        progress_percentage=status_data.get("progress_percentage"),
        current_step=status_data.get("current_step"),
        started_at=status_data.get("started_at"),
        completed_at=status_data.get("completed_at"),
        error_message=status_data.get("error_message")
    )


@router.get("/result/{task_id}")
async def get_background_analysis_result(task_id: str):
    """
    백그라운드 분석 결과 조회
    
    - **task_id**: 작업 ID
    
    Returns:
        분석 결과 (완료된 경우)
    """
    
    if task_id not in analysis_status_store:
        raise HTTPException(
            status_code=404,
            detail="Analysis task not found"
        )
    
    status_data = analysis_status_store[task_id]
    
    if status_data["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Analysis not completed yet. Current status: {status_data['status']}"
        )
    
    return status_data.get("result")


@router.get("/history/{test_history_id}", response_model=AnalysisHistoryResponse)
async def get_analysis_history(
    test_history_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    테스트의 분석 이력 조회
    
    - **test_history_id**: 테스트 히스토리 ID
    
    Returns:
        분석 이력 목록
    """
    
    # TODO: Repository Pattern으로 분석 이력 구현
    # 현재는 빈 응답 반환
    return AnalysisHistoryResponse(
        test_history_id=test_history_id,
        total_count=0,
        analyses=[]
    )


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


@router.get("/performance/stats")
async def get_performance_statistics():
    """
    AI 분석 성능 통계 조회
    
    Returns:
        모델별 성능 통계
    """
    
    model_manager = get_model_manager()
    stats = model_manager.get_performance_stats()
    
    return {
        "performance_statistics": stats,
        "recommendations": _generate_model_recommendations(stats)
    }


async def _run_background_comprehensive_analysis(
    task_id: str,
    ai_service: AIAnalysisService,
    db_sync: Session,
    db_async: AsyncSession,
    request: ComprehensiveAnalysisRequest
):
    """백그라운드 종합 분석 실행"""
    
    try:
        # 상태 업데이트: 실행 중
        analysis_status_store[task_id].update({
            "status": "running",
            "progress_percentage": 10,
            "current_step": "Collecting test data"
        })
        
        # 분석 유형 수에 따른 진행률 계산
        analysis_types = request.analysis_types or [
            AnalysisType.COMPREHENSIVE,
            AnalysisType.RESPONSE_TIME,
            AnalysisType.TPS,
            AnalysisType.ERROR_RATE,
            AnalysisType.RESOURCE_USAGE
        ]
        
        total_steps = len(analysis_types)
        completed_steps = 0
        
        # 각 분석 단계별 진행률 업데이트
        for i, analysis_type in enumerate(analysis_types, 1):
            analysis_status_store[task_id].update({
                "progress_percentage": 10 + (i * 70 // total_steps),
                "current_step": f"Performing {analysis_type.value} analysis"
            })
            
            # 실제로는 여기서 각 분석을 개별적으로 수행할 수 있음
            # 현재는 전체 분석을 한번에 수행
            
        # 분석 수행
        result = await ai_service.perform_comprehensive_analysis(
            db_sync=db_sync,
            db_async=db_async,
            test_history_id=request.test_history_id,
            analysis_types=request.analysis_types,
            model_name=request.model_name,
            priority=request.priority,
            comparison_test_ids=request.comparison_test_ids
        )
        
        # 상태 업데이트: 완료
        analysis_status_store[task_id].update({
            "status": "completed",
            "progress_percentage": 100,
            "current_step": "Analysis completed",
            "completed_at": datetime.now(),
            "result": result.dict()
        })
        
    except Exception as e:
        # 상태 업데이트: 실패
        analysis_status_store[task_id].update({
            "status": "failed",
            "progress_percentage": 0,
            "current_step": "Analysis failed",
            "completed_at": datetime.now(),
            "error_message": str(e)
        })


def _generate_model_recommendations(stats: Dict[str, Any]) -> List[str]:
    """성능 통계를 바탕으로 모델 사용 권장사항 생성"""
    
    recommendations = []
    
    if not stats.get("models"):
        recommendations.append("No performance data available yet. Try running some analyses first.")
        return recommendations
    
    # 최고 성능 모델 찾기
    best_model = None
    best_score = 0
    
    for model_name, model_stats in stats["models"].items():
        # 성공률, 품질 점수, 속도를 종합한 점수 계산
        success_rate = model_stats.get("success_rate", 0)
        quality_score = model_stats.get("avg_quality_score", 0)
        speed_score = 1000 / max(model_stats.get("avg_duration_ms", 1000), 100)  # 속도 점수 (빠를수록 높음)
        
        overall_score = (success_rate * 0.5) + (quality_score * 0.3) + (speed_score * 0.2)
        
        if overall_score > best_score:
            best_score = overall_score
            best_model = model_name
    
    if best_model:
        recommendations.append(f"Best performing model: {best_model}")
    
    # 성공률 낮은 모델 경고
    for model_name, model_stats in stats["models"].items():
        if model_stats.get("success_rate", 1) < 0.8:
            recommendations.append(f"Warning: {model_name} has low success rate ({model_stats['success_rate']:.1%})")
    
    return recommendations