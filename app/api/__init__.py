from fastapi import APIRouter

from app.api.home_routes import router as home_router
from app.api.swagger_analyze_router import router as swagger_analyze_router

api_router = APIRouter()
api_router.include_router(home_router)
api_router.include_router(swagger_analyze_router)
