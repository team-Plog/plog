from fastapi import FastAPI
from app.api import api_router
import uvicorn
app = FastAPI(
    title="Metric Vault API",
    description="Metric 정보를 수집하고 분석하는 백엔드 API입니다.",
    version="1.0.0",
    docs_url="/api/swagger"
)
app.include_router(api_router)