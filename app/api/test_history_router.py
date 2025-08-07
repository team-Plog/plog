from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pyasn1_modules.rfc5934 import StatusCode
from sqlalchemy.orm import Session

from app.common.response.code import SuccessCode
from app.common.response.response_template import ResponseTemplate
from app.db import get_db
from app.services.test_history_service import get_test_histories, get_test_history_by_id, get_test_histories_with_project_info
from app.dto.test_history.test_history_response import TestHistoryResponse
from app.dto.test_history.test_history_simple_response import TestHistorySimpleResponse

router = APIRouter()

# @router.get(
#     "",
#     response_model=List[TestHistoryResponse],
#     summary="테스트 기록 목록 조회",
#     description="실행된 로드 테스트 기록들을 최신순으로 조회합니다. 페이지네이션을 지원합니다."
# )
# def get_test_history_list(
#     skip: int = 0,
#     limit: int = 100,
#     db: Session = Depends(get_db)
# ):
#     return get_test_histories(db, skip=skip, limit=limit)


@router.get(
    "/simple", 
    response_model=List[TestHistorySimpleResponse],
    summary="메인보드용 테스트 기록 간단 조회",
    description="""
    메인보드에서 사용할 테스트 기록들을 간단한 형태로 조회합니다. 프로젝트명, 테스트명, 완료일시, 상태를 포함합니다.
    
    상태의 경우 실행된 테스트를 추적하는 기능이 완성되지 않아 테스트 완료 상태가 나타나지 않습니다.
    
    status_datetime의 경우 테스트가 완료되지 않았으면 시작 시간, 완료되었으면 완료 시간으로 응답을 반환합니다.
    """
)
def get_test_history_simple_list(
    page: int = 0,
    size: int = 100,
    db: Session = Depends(get_db)
):
    results = get_test_histories_with_project_info(db, size=size, page=page)
    
    simple_responses = []

    # TODO k3s job 조회 코드 추가 필요,
    # job이 있는 경우 - 실행 중
    # job이 없는 경우 - 실행 전
    # job 에러인 경우 - 에러 발생
    for test_history in results:
        # 테스트 상태 결정
        if test_history.is_completed:
            test_status = "테스트 완료"
        elif not test_history.is_completed:
            test_status = "실행 중"
        else:
            test_status = "실행 전"
        
        simple_responses.append(TestHistorySimpleResponse(
            test_history_id=test_history.id,
            project_id=test_history.project.id,
            project_title=test_history.project.title or "알 수 없는 프로젝트",
            test_title=test_history.title,
            status_datetime=test_history.completed_at if test_history.completed_at else test_history.tested_at,
            test_status=test_status
        ))
    
    return ResponseTemplate.success(SuccessCode.SUCCESS_CODE, simple_responses)

