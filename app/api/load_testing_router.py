import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.load_test_request import LoadTestRequest
from app.services.load_test_service import generate_k6_script

from k8s.k8s_service import create_k6_job_with_dashboard
from app.services import create_test_history

router = APIRouter()

@router.post(
    path="",
    summary="gui 기반 입력값 k6 부하테스트 스크립트 생성 API",
    description="테스트할 엔드포인트와 시나리오 정보를 입력받아 K6 스크립트를 생성합니다.",
)
async def create_load_testing_script_by_gui(
        request: LoadTestRequest,
        db: Session = Depends(get_db),
):
    # 1. 스크립트 생성
    script_content: str = generate_k6_script(request, db)

    # 2. 파일로 저장
    # TODO 생성된 파일 제거 유무 추가
    file_name = generate_unique_filename()
    script_path = f"/k6-scripts/{file_name}"
    with open(script_path, "w") as f:
        f.write(script_content)

    # 3. test history 생성 및 연관관계
    create_test_history(request, file_name, db)

    # 4. k6 run job 생성
    job_name = generate_unique_job_name()
    create_k6_job_with_dashboard(
        job_name,
        file_name,
        "k6-script-pvc"
    )

    return {
        "message": "부하테스트 스크립트 생성, 기록 및 Job 실행 완료",
        "file_name": file_name,
    }

def generate_unique_filename(prefix="load_test", ext="js"):
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:6]
    return f"{prefix}_{timestamp}_{unique_id}.{ext}"

def generate_unique_job_name(prefix="job"):
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:6]
    return f"{prefix}-{timestamp}-{unique_id}"