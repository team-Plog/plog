from fastapi import FastAPI
from app.api import api_router
from app.db.database import engine
from app.db import models
from app.exceptionhandler import register_exception_handler
app = FastAPI(
    title="Metric Vault API",
    description="Metric 정보를 수집하고 분석하는 백엔드 API입니다.",
    version="1.0.0",
    docs_url="/api/swagger"
)
app.include_router(api_router)

# init table
models.Base.metadata.create_all(bind=engine)
register_exception_handler(app)