from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.test_history_service import get_test_histories, get_test_history_by_id, get_test_histories_with_project_info
from app.dto.test_history.test_history_response import TestHistoryResponse
from app.dto.test_history.test_history_simple_response import TestHistorySimpleResponse

router = APIRouter()


@router.get(
    "/", 
    response_model=List[TestHistoryResponse],
    summary="테스트 기록 목록 조회",
    description="실행된 로드 테스트 기록들을 최신순으로 조회합니다. 페이지네이션을 지원합니다."
)
def get_test_history_list(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    return get_test_histories(db, skip=skip, limit=limit)


@router.get(
    "/simple", 
    response_model=List[TestHistorySimpleResponse],
    summary="메인보드용 테스트 기록 간단 조회",
    description="메인보드에서 사용할 테스트 기록들을 간단한 형태로 조회합니다. 프로젝트명, 테스트명, 완료일시, 상태를 포함합니다."
)
def get_test_history_simple_list(
    page: int = 0,
    size: int = 100,
    db: Session = Depends(get_db)
):
    results = get_test_histories_with_project_info(db, size=size, page=page)
    
    simple_responses = []
    for test_history, project_title in results:
        # 테스트 상태 결정
        if test_history.is_completed:
            test_status = "테스트 완료"
        elif test_history.job_name:  # job_name이 있으면 실행 중
            test_status = "실행 중"
        else:
            test_status = "실행 전"
        
        simple_responses.append(TestHistorySimpleResponse(
            project_title=project_title or "알 수 없는 프로젝트",
            test_title=test_history.title,
            completed_at=test_history.completed_at,
            test_status=test_status
        ))
    
    return simple_responses


@router.get(
    "/{test_history_id}", 
    response_model=TestHistoryResponse,
    summary="테스트 기록 상세 조회",
    description="특정 테스트 기록의 상세 정보와 시나리오, 스테이지 정보를 함께 조회합니다."
)
def get_test_history_detail(
    test_history_id: int,
    db: Session = Depends(get_db)
):
    test_history = get_test_history_by_id(db, test_history_id)
    if not test_history:
        raise HTTPException(status_code=404, detail="Test history not found")
    return test_history