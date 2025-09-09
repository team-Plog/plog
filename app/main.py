import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api import api_router
from app.core.config import settings
from app.models.sqlite import models
from app.sse import sse_router
from app.models.sqlite.database import engine
from app.common.exceptionhandler import register_exception_handler
from app.common.middleware.cors_middleware import register_cors_middleware
from app.scheduler.k6_job_scheduler import start_scheduler, stop_scheduler
from app.scheduler.server_pod_scheduler import start_scheduler as start_pod_scheduler, stop_scheduler as stop_pod_scheduler
from app.scheduler.cache_cleanup_scheduler import start_cache_scheduler, stop_cache_scheduler
from k8s.k8s_client import v1_core

# 테스트 임시 import
from k8s.pod_service import PodService

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # 시작 시 실행
    logger.info("Starting Metric Vault API...")
    
    # 데이터베이스 테이블 초기화
    models.Base.metadata.create_all(bind=engine)
    
    # kubernetes connection test
    try:
        pods = v1_core.list_namespaced_pod("default")
        logger.info(f"Kubernetes connection successful. Found {len(pods.items)} pods in default namespace")
        for pod in pods.items[:3]:  # 처음 3개만 로그
            logger.info(f"Pod: {pod.metadata.name}")
    except Exception as e:
        logger.error(f"Kubernetes connection test failed: {e}")


    pod_service = PodService("test")
    test_data = pod_service.get_running_pods()
    print("test_data = ", test_data)
    
    # k6 Job 스케줄러 시작
    try:
        start_scheduler()
        logger.info("K6 Job Scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start K6 Job Scheduler: {e}")
    
    # Server Pod 스케줄러 시작
    try:
        start_pod_scheduler()
        logger.info("Server Pod Scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start Server Pod Scheduler: {e}")
    
    # 캐시 정리 스케줄러 시작
    try:
        start_cache_scheduler()
        logger.info("Cache cleanup scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start cache cleanup scheduler: {e}")
    
    yield
    
    # 종료 시 실행
    logger.info("Shutting down Metric Vault API...")
    
    # 스케줄러 중지
    try:
        stop_scheduler()
        logger.info("K6 Job Scheduler stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop K6 Job Scheduler: {e}")
    
    try:
        stop_pod_scheduler()
        logger.info("Server Pod Scheduler stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop Server Pod Scheduler: {e}")
    
    # 캐시 정리 스케줄러 중지
    try:
        stop_cache_scheduler()
        logger.info("Cache cleanup scheduler stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop cache cleanup scheduler: {e}")


app = FastAPI(
    title="Metric Vault API",
    description="Metric 정보를 수집하고 분석하는 백엔드 API입니다.",
    version="1.0.0",
    docs_url="/api/swagger",
    lifespan=lifespan
)

app.include_router(api_router)
app.include_router(sse_router)

register_cors_middleware(app)
register_exception_handler(app)