from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from pydantic import HttpUrl
from sqlalchemy.orm import Session
from app.db import get_db
from app.db.models import OpenAPISpecModel

from app.models.openapi import OpenAPISpec
from app.services import *

router = APIRouter()

@router.post(
    path="/analyze",
    summary="엔드포인트 분석 API",
    description="openapi url를 통해 애플리케이션 openapi 정보(버전, 설명, 엔드포인트)를 저장한다.",
)
async def analyze_swagger(
    db: Session = Depends(get_db),
    openapi_url: HttpUrl = Body(default="http://localhost:8080/v3/api-docs", embed=True)
):
    # 1. analyze
    analyze_result: OpenAPISpecModel = await analyze_openapi_spec(str(openapi_url))

    # 2. save
    saved_open_api_spec: OpenAPISpecModel = await save_openapi_spec(db, analyze_result)

    # 3. converter
    response = OpenAPISpec.from_orm(saved_open_api_spec).model_dump()

    return JSONResponse(
        status_code=200,
        content={
            "data": response
        }
    )

@router.get(
    path="",
    summary="OpenAPI 명세 리스트 조회 API",
    description="저장된 OpenAPI 명세들을 리스트 형태로 반환한다."
)
async def get_openapi_specs(
    db: Session = Depends(get_db)
):
    # DB에서 모든 OpenAPISpecModel 조회
    openapi_specs = db.query(OpenAPISpecModel).all()

    # Pydantic 모델로 변환
    response = [OpenAPISpec.from_orm(spec).model_dump() for spec in openapi_specs]

    return JSONResponse(
        status_code=200,
        content={
            "data": response
        }
    )
