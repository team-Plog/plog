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

@router.post("/analyze")
async def analyze_swagger(
    db: Session = Depends(get_db),
    swagger_url: HttpUrl = Body(..., embed=True)
):
    try:
        analyze_result: OpenAPISpec = await analyze_openapi_spec(str(swagger_url))
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

