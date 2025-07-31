from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.test_history_service import get_test_histories, get_test_history_by_id
from app.dto.test_history.test_history_response import TestHistoryResponse

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