from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.common.response.code import SuccessCode
from app.common.response.response_template import ResponseTemplate
from app.db import get_db
from app.services.test_history_service import get_test_histories, get_test_history_by_id, get_test_histories_with_project_info, get_test_histories_by_project_id
from app.dto.test_history.test_history_response import TestHistoryResponse
from app.dto.test_history.test_history_simple_response import TestHistorySimpleResponse
from app.dto.test_history.test_history_detail_response import TestHistoryDetailResponse

router = APIRouter()

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


@router.get(
    "/projects/{project_id}",
    response_model=List[TestHistorySimpleResponse],
    summary="프로젝트별 테스트 기록 조회",
    description="""
    ## 개요
    특정 프로젝트에 속한 모든 테스트 기록을 간단한 형태로 조회합니다.
    
    ## 요청 파라미터
    - **project_id** (path): 조회할 프로젝트의 ID (정수)
    
    ## 응답 형식
    ```json
    {
        "code": "SUCCESS_CODE",
        "message": "성공적으로 처리되었습니다.",
        "data": [
            {
                "test_history_id": 1,
                "project_id": 1,
                "project_title": "프로젝트명",
                "test_title": "로드테스트 제목",
                "status_datetime": "2024-01-01T10:30:00.000Z",
                "test_status": "테스트 완료"
            }
        ]
    }
    ```
    
    ## 상태값 설명
    - **테스트 완료**: 테스트가 성공적으로 완료됨
    - **실행 중**: 테스트가 현재 진행 중
    - **실행 전**: 테스트가 아직 시작되지 않음
    
    ## 사용 예시
    - 프로젝트 대시보드에서 테스트 기록 목록 표시
    - 특정 프로젝트의 테스트 실행 이력 조회
    """
)
def get_test_histories_by_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    """특정 프로젝트의 테스트 기록들을 조회합니다."""
    test_histories = get_test_histories_by_project_id(db, project_id)
    
    if not test_histories:
        return ResponseTemplate.success(SuccessCode.SUCCESS_CODE, [])
    
    simple_responses = []
    
    for test_history in test_histories:
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


@router.get(
    "/{test_history_id}/details",
response_model=TestHistoryDetailResponse,
    summary="테스트 기록 상세 조회",
    description="""
    ## 개요
    특정 테스트 기록의 모든 상세 정보를 조회합니다. 전체 테스트 메트릭, 시나리오별 상세 정보, 엔드포인트 정보, 스테이지별 설정을 포함합니다.
    
    ## 요청 파라미터
    - **test_history_id** (path): 조회할 테스트 기록의 ID (정수)
    
    ## 응답 형식
    ```json
    {
        "code": "SUCCESS_CODE",
        "message": "성공적으로 처리되었습니다.",
        "data": {
            "test_history_id": 1,
            "title": "API 성능 테스트",
            "description": "사용자 인증 API 로드테스트",
            "target_tps": 100.0,
            "tested_at": "2024-01-01T10:00:00.000Z",
            "is_completed": true,
            "completed_at": "2024-01-01T10:30:00.000Z",
            "project_id": 1,
            "actual_tps": 95.5,
            "avg_response_time": 120.5,
            "max_response_time": 850.2,
            "min_response_time": 45.1,
            "p95_response_time": 320.8,
            "error_rate": 0.02,
            "total_requests": 18000,
            "failed_requests": 360,
            "max_vus": 50,
            "test_duration": 1800.0,
            "scenarios": [
                {
                    "id": 1,
                    "name": "로그인 시나리오",
                    "endpoint_id": 1,
                    "endpoint": {
                        "id": 1,
                        "path": "/api/auth/login",
                        "method": "POST",
                        "summary": "사용자 로그인",
                        "description": "이메일과 패스워드로 로그인"
                    },
                    "executor": "ramping-vus",
                    "think_time": 1.0,
                    "scenario_name": "login-scenario-1",
                    "actual_tps": 48.2,
                    "avg_response_time": 115.3,
                    "p95_response_time": 290.1,
                    "error_rate": 0.015,
                    "total_requests": 8640,
                    "failed_requests": 130,
                    "stages": [
                        {
                            "id": 1,
                            "duration": "5m",
                            "target": 10
                        },
                        {
                            "id": 2,
                            "duration": "10m",
                            "target": 50
                        }
                    ]
                }
            ]
        }
    }
    ```
    
    ## 응답 데이터 상세
    
    ### 테스트 기본 정보
    - **test_history_id**: 테스트 기록 고유 ID
    - **title**: 테스트 제목
    - **description**: 테스트 설명
    - **target_tps**: 목표 TPS (초당 트랜잭션)
    - **tested_at**: 테스트 시작 시간
    - **is_completed**: 테스트 완료 여부
    - **completed_at**: 테스트 완료 시간
    
    ### 전체 테스트 메트릭
    - **actual_tps**: 실제 달성한 TPS
    - **avg_response_time**: 평균 응답시간 (ms)
    - **max_response_time**: 최대 응답시간 (ms)
    - **min_response_time**: 최소 응답시간 (ms)
    - **p95_response_time**: 95 퍼센타일 응답시간 (ms)
    - **error_rate**: 에러율 (0.0 ~ 1.0)
    - **total_requests**: 총 요청 수
    - **failed_requests**: 실패한 요청 수
    - **max_vus**: 최대 가상 사용자 수
    - **test_duration**: 테스트 지속 시간 (초)
    
    ### 시나리오별 상세 정보
    - 각 시나리오의 개별 메트릭
    - 연결된 엔드포인트의 상세 정보 (경로, 메서드, 설명)
    - 시나리오별 스테이지 설정 (지속시간, 목표 사용자 수)
    
    ## 에러 응답
    - **404 Not Found**: 해당 ID의 테스트 기록이 존재하지 않음
    
    ## 사용 예시
    - 테스트 상세 결과 페이지 표시
    - 성능 분석 대시보드 데이터 제공
    - 테스트 리포트 생성
    """
)
def get_test_history_details(
    test_history_id: int,
    db: Session = Depends(get_db)
):
    """테스트 기록의 상세 정보를 조회합니다."""
    test_history = get_test_history_by_id(db, test_history_id)
    
    if not test_history:
        raise HTTPException(status_code=404, detail="Test history not found")
    
    return ResponseTemplate.success(SuccessCode.SUCCESS_CODE, test_history)

