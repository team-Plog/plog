import httpx
from fastapi import APIRouter, Body, HTTPException
from pydantic import HttpUrl
from app.services import *

router = APIRouter()

@router.post("/analyze")
async def analyze_swagger(
    swagger_url: HttpUrl = Body(..., embed=True)
):
    try:
        return await analyze_openapi_spec(str(swagger_url))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch OpenAPI spec: {e}")

