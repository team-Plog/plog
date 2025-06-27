from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request
import logging
import traceback

logger = logging.getLogger(__name__)

def register_exception_handler(app: FastAPI):

    # 예상치 못한 모든 예외 처리
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        tb_str = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        logger.error(f"Unhandled exception occurred: {exc}\nStack trace:\n{tb_str}", exc_info=True)
        return JSONResponse(status_code=500, content={"message": "Internal Server Error"})




