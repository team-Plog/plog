from app.common.response.code.base_code import BaseCode

class SuccessCode(BaseCode):
    SUCCESS_CODE = ("요청 처리에 성공하였습니다.", 200)
    CREATED = ("리소스를 정상적으로 생성하였습니다.", 201)