from fastapi import FastAPI

from app.api import api_router
from app.sse import sse_router
from app.db.sqlite.database import engine
from app.db.sqlite import models
from app.common.exceptionhandler import register_exception_handler
from app.common.middleware.cors_middleware import register_cors_middleware
from k8s.k8s_client import v1_core
app = FastAPI(
    title="Metric Vault API",
    description="Metric 정보를 수집하고 분석하는 백엔드 API입니다.",
    version="1.0.0",
    docs_url="/api/swagger"
)
app.include_router(api_router)
app.include_router(sse_router)

register_cors_middleware(app)


# init table
models.Base.metadata.create_all(bind=engine)
register_exception_handler(app)

# kubernetes connection test
pods = v1_core.list_namespaced_pod("default")
for pod in pods.items:
    print(pod.metadata.name)