from fastapi import APIRouter

from app.api.home_routes import router as home_router

api_router = APIRouter()
api_router.include_router(home_router)