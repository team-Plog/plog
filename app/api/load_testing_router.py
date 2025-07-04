import subprocess
from typing import Dict

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.load_test_request import LoadTestRequest, ScenarioConfig
from app.services.load_test_service import generate_k6_script

router = APIRouter()

K6_EXEC_API_URL = "http://localhost:31000/run-k6"  # 예: http://192.168.1.10:31000/run-k6

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
    script_path = "/Users/jiwonp/mnt/k6-scripts/load_test_script.js"
    with open(script_path, "w") as f:
        f.write(script_content)

        # 3. k6 실행 요청 전송 (express.js API)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(K6_EXEC_API_URL, json={
                    "filename": "load_test_script.js"
                })
                response.raise_for_status()
                return {"result": response.json()}
        except httpx.HTTPError as e:
            return {"error": str(e)}