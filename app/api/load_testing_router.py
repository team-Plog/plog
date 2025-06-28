from typing import Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.load_test_request import LoadTestRequest, ScenarioConfig
from app.services.load_test_service import generate_k6_script

router = APIRouter()

class K6ScriptResponse(BaseModel):
    script: str

@router.post(
    path="",
    summary="gui 기반 입력값 k6 부하테스트 스크립트 생성 API",
    description="테스트할 엔드포인트와 시나리오 정보를 입력받아 K6 스크립트를 생성합니다.",
)
async def create_load_testing_script_by_gui(
        request: LoadTestRequest,
        db: Session = Depends(get_db),
):
    script: str = generate_k6_script(request, db)
    return script