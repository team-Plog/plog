from fastapi import FastAPI, Request
import logging
import traceback

from app.common.exception.api_exception import ApiException
from app.common.response.code import FailureCode
from app.common.response.response_template import ResponseTemplate

logger = logging.getLogger(__name__)

def register_exception_handler(app: FastAPI):
    # 특정 사용자 정의 예외(ApiException) 처리
    @app.exception_handler(ApiException)
    async def api_exception_handler(request: Request, exc: ApiException):
        # 디버깅 할 때 exc_info = True -> stack trace 출력
        logger.error(f"ApiException occurred: {exc.code}", exc_info=True)
        return ResponseTemplate.fail(
            code=exc.code,
            custom_message=exc.message,
        )

    # 예상치 못한 모든 예외 처리
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        tb_str = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        logger.error(f"Unhandled exception occurred: {exc}\nStack trace:\n{tb_str}", exc_info=True)
        return ResponseTemplate.fail(
            FailureCode.INTERNAL_SERVER_ERROR,
        )
