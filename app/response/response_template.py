from typing import Any

from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from app.response.code import BaseCode

class ResponseTemplate:
    def __init__(self, success: bool, message: str, status_code: int, data: Any = None):
        self.success = success
        self.message = message
        self.data = data
        self.status_code = status_code

    @classmethod
    def success(cls, code: BaseCode, data: Any = None):
        message, status_code = code.message(), code.status_code()

        response_body = {
            "success": True,
            "message": message,
            "data": data,
            "status_code": status_code,
        }
        return JSONResponse(content=jsonable_encoder(response_body), status_code=200)

    @classmethod
    def fail(cls, code: BaseCode, custom_message: str = None, data: Any = None):
        # 응답을 바로 만들어서 반환
        status_code = code.status_code()
        message = custom_message or code.message()

        response_body = {
            "success": False,
            "message": message,
            "data": data,
            "status_code": status_code,
        }
        return JSONResponse(content=jsonable_encoder(response_body), status_code=status_code)