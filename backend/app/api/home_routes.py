from fastapi import APIRouter

router = APIRouter()

@router.get(
    path="/",
    summary = "health check",
    description = "health check 용 엔드포인트"
)
async def home():
    return "ok"