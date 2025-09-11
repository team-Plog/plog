from fastapi import APIRouter

from app.api.home_routes import router as home_router
from app.api.openapi_router import router as swagger_analyze_router
from app.api.load_testing_router import router as load_testing_router
from app.api.project_router import router as project_router
from app.api.test_history_router import router as test_history_router
from app.api.endpoint_router import router as endpoint_router
from app.api.scheduler_router import router as scheduler_router
from app.api.debug_router import router as debug_router
from app.api.analysis_router import router as analysis_router

api_router = APIRouter()
api_router.include_router(
    home_router,
    tags=["home"],
)

api_router.include_router(
    swagger_analyze_router,
    prefix= "/openapi",
    tags=["OpenAPI Analyze"]
)

api_router.include_router(
    load_testing_router,
    prefix= "/load-testing",
    tags=["Load Testing"]
)

api_router.include_router(
    project_router,
    prefix="/project",
    tags=["Project"]
)

api_router.include_router(
    test_history_router,
    prefix="/test-history",
    tags=["Test History"]
)

api_router.include_router(
    endpoint_router,
    prefix="/endpoint",
    tags=["Endpoint"]
)

api_router.include_router(
    scheduler_router,
    prefix="/scheduler",
    tags=["Job Scheduler"]
)

api_router.include_router(
    debug_router,
    tags=["Debug"]
)

api_router.include_router(
    analysis_router,
    tags=["AI Analysis"]
)