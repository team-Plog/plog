import httpx
from fastapi import APIRouter, Body, HTTPException, Depends
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
    try:
        analyze_result: OpenAPISpec = await analyze_openapi_spec(str(openapi_url))
        saved_open_api_spec: OpenAPISpecModel = await save_openapi_spec(db, analyze_result)
        response = OpenAPISpec.from_orm(saved_open_api_spec).model_dump()

        return JSONResponse(
            status_code=200,
            content={
                "data": response
            }
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch OpenAPI spec: {e}")
