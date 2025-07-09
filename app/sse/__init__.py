from app.sse.sse_k6data import router as sse_k6data_router
from fastapi import APIRouter

sse_router = APIRouter()
sse_router.include_router(sse_k6data_router)

__all__ = ["sse_router"]