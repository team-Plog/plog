from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.common.response.code import SuccessCode
from app.common.response.response_template import ResponseTemplate
from app.db import get_db
from app.services.test_history_service import (
    get_test_histories, 
    get_test_history_by_id, 
    get_test_histories_with_project_info, 
    get_test_histories_by_project_id,
    build_test_history_detail_response
)
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
        "success": true,
        "message": "요청 처리에 성공하였습니다.",
        "data": {
            "test_history_id": 1,
            "project_id": 3,
            "title": "테스트 제목",
            "description": "테스트 상세 내용",
            "is_completed": true,
            "completed_at": "2025-08-07T15:07:08.300036",
            "tested_at": "2025-08-08T00:06:42.954398",
            "job_name": "job20250807150642466f45",
            "k6_script_file_name": "load_test_20250807_150642_0aced0.js",
            "overall": {
                "target_tps": 100,
                "total_requests": 18000,
                "failed_requests": 360,
                "test_duration": 1800.0,
                "tps": {
                    "max": 98.7,
                    "min": 30,
                    "avg": 70
                },
                "response_time": {
                    "max": 850.2,
                    "min": 45.1,
                    "avg": 120.5,
                    "p50": 95.3,
                    "p95": 320.8,
                    "p99": 450.2
                },
                "error_rate": {
                    "max": 0.05,
                    "min": 0.0,
                    "avg": 0.02
                },
                "vus": {
                    "max": 50,
                    "min": 10,
                    "avg": 30.5
                }
            },
            "scenarios": [
                {
                    "scenario_history_id": 1,
                    "name": "시나리오 제목",
                    "scenario_tag": "테스트 시나리오 태그",
                    "total_requests": 8640,
                    "failed_requests": 130,
                    "test_duration": 900.0,
                    "response_time_target": 1.0,
                    "error_rate_target": 1.0,
                    "think_time": 1,
                    "executor": "constant-vus",
                    "endpoint": {
                        "endpoint_id": 5,
                        "method": "GET",
                        "path": "/api/io/sleep/500",
                        "description": "500ms 지연을 줘서 실제 I/O 작업을 모방하는 테스트 API",
                        "summary": "I/O 지연 테스트"
                    },
                    "tps": {
                        "max": 48.7,
                        "min": 20,
                        "avg": 35.2
                    },
                    "response_time": {
                        "max": 650.1,
                        "min": 480.3,
                        "avg": 520.8,
                        "p50": 515.2,
                        "p95": 580.3,
                        "p99": 620.7
                    },
                    "error_rate": {
                        "max": 0.02,
                        "min": 0.0,
                        "avg": 0.015
                    },
                    "stages": [
                        {
                            "stage_history_id": 1,
                            "duration": "10s",
                            "target": 10
                        }
                    ]
                }
            ]
        },
        "status_code": 200
    }
    ```
    
    ## 응답 데이터 상세
    
    ### 테스트 기본 정보
    - **test_history_id**: 테스트 기록 고유 ID
    - **project_id**: 프로젝트 ID
    - **title**: 테스트 제목
    - **description**: 테스트 설명
    - **is_completed**: 테스트 완료 여부
    - **completed_at**: 테스트 완료 시간
    - **tested_at**: 테스트 시작 시간
    - **job_name**: k6 Job 이름
    - **k6_script_file_name**: k6 스크립트 파일명
    
    ### Overall 섹션 (전체 테스트 메트릭)
    - **target_tps**: 목표 TPS (초당 트랜잭션)
    - **total_requests**: 총 요청 수
    - **failed_requests**: 실패한 요청 수
    - **test_duration**: 테스트 지속 시간 (초)
    - **tps**: TPS 메트릭 {max, min, avg}
    - **response_time**: 응답시간 메트릭 {max, min, avg, p50, p95, p99} (ms)
    - **error_rate**: 에러율 메트릭 {max, min, avg} (0.0 ~ 1.0)
    - **vus**: 가상 사용자 수 메트릭 {max, min, avg}
    
    ### Scenarios 섹션 (시나리오별 상세 정보)
    - **scenario_history_id**: 시나리오 기록 고유 ID
    - **name**: 시나리오 제목
    - **scenario_tag**: 테스트 시나리오 태그 (쿼리용 내부 식별자)
    - **total_requests/failed_requests**: 시나리오별 요청 통계
    - **test_duration**: 시나리오 테스트 시간 (초)
    - **response_time_target/error_rate_target**: 목표 메트릭
    - **think_time**: 사고 시간 (초)
    - **executor**: k6 실행자 타입
    - **endpoint**: 연결된 엔드포인트 상세 정보 (method, path, description, summary)
    - **tps/response_time/error_rate**: 시나리오별 메트릭 (overall과 동일한 구조)
    - **stages**: 시나리오의 스테이지 설정 목록 (duration, target)
    
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
    
    response_data:TestHistoryDetailResponse = build_test_history_detail_response(test_history)
    
    return ResponseTemplate.success(SuccessCode.SUCCESS_CODE, response_data)

