import logging
import os
import uuid
from datetime import datetime

from dotenv import load_dotenv
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.response.code import SuccessCode
from app.common.response.response_template import ResponseTemplate
from app.db import get_db
from app.dto.load_test.load_test_request import LoadTestRequest
from app.services.load_test_service import generate_k6_script
from app.services.test_history_service import save_test_history

from k8s.k8s_service import create_k6_job_with_dashboard
from app.services import save_test_history

load_dotenv()

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post(
    path="",
    summary="K6 부하테스트기 실행 API",
    description="""
    테스트 정보들을 입력받아 내부적으로 K6 테스트 스크립트를 생성하고 Kubernetes에서 부하테스트를 진행합니다.
    
    ## 요청 파라미터:
    
    ### 기본 정보
    - title: 테스트 제목 (string) - 테스트 실행을 식별하기 위한 이름
    - description: 테스트 상세 설명 (string) - 테스트 목적이나 특이사항 기록
    - target_tps: 목표 TPS (float, optional) - 전체 테스트의 목표 처리량, 결과 분석 시 기준값으로 사용
    
    ### scenarios (배열)
    각 시나리오는 특정 엔드포인트에 대한 부하테스트 설정을 정의합니다:
    
    #### 시나리오 기본 설정
    - name: 시나리오 이름 (string) - K6 스크립트 내에서 함수명으로 사용
    - endpoint_id: 엔드포인트 ID (int) - 데이터베이스에 등록된 API 엔드포인트 식별자
    - executor: K6 실행 모드 (string)
      - constant-vus: 일정한 가상 사용자 수로 지속 실행
      - ramping-vus: 단계적으로 가상 사용자 수를 증감
    - think_time: 요청 간 대기시간 (float) - 단위: 초, 실제 사용자 행동 시뮬레이션
    
    #### 성능 목표 설정 (선택사항)
    - response_time_target: 응답시간 목표 (float, optional) - 단위: ms
    - error_rate_target: 에러율 목표 (float, optional) - 단위: %
    
    #### stages (배열) - executor에 따른 실행 단계 정의
    각 stage는 테스트 진행 단계를 나타냅니다:
    - duration: 단계 지속시간 (string) - 형식: "10s", "2m", "1h"
    - target: 목표 가상 사용자 수 (int)
    
    executor별 stages 사용법:
    - constant-vus: 첫 번째 stage만 사용 (vus와 duration 값)
    - ramping-vus: 모든 stages 사용하여 단계적 부하 증감
    
    ## 응답값:
    - file_name: 생성된 K6 스크립트 파일명
    - job_name: Kubernetes에서 실행되는 Job 이름
    
    ## 동작 과정:
    1. 요청 데이터를 기반으로 K6 JavaScript 스크립트 생성
    2. 스크립트를 PVC에 파일로 저장
    3. 테스트 히스토리를 SQLite에 기록
    4. Kubernetes Job으로 K6 실행 (InfluxDB 연동 및 웹 대시보드 활성화)
    """,
)
async def create_load_testing_script_by_gui(
        request: LoadTestRequest,
        db: Session = Depends(get_db),
):
    # 1. 스크립트 생성
    job_name = generate_unique_job_name()
    script_content: str = generate_k6_script(request, job_name, db)

    logger.info(f"생성된 스크립트 파일 디버깅: {script_content}")

    # 2. 파일로 저장
    # TODO 생성된 파일 제거 유무 추가
    file_name = generate_unique_filename()
    # script_path = f"/k6-scripts/{file_name}"
    script_path = f"{os.getenv('K6_SCRIPT_FILE_FOLDER', '/mnt/k6-scripts')}/{file_name}"
    with open(script_path, "w") as f:
        f.write(script_content)

    # 3. test history 생성 및 연관관계
    save_test_history(
        request,
        file_name,
        job_name,
        db
    )

    # 4. k6 run job 생성
    create_k6_job_with_dashboard(
        job_name,
        file_name,
        "k6-script-pvc"
    )

    return ResponseTemplate.success(
        SuccessCode.SUCCESS_CODE, {
        "file_name": file_name,
        "job_name": job_name,
    })

def generate_unique_filename(prefix="load_test", ext="js"):
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:6]
    return f"{prefix}_{timestamp}_{unique_id}.{ext}"

def generate_unique_job_name(prefix="job"):
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:6]
    return f"{prefix}{timestamp}{unique_id}"
