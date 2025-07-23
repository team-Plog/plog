from app.response.code.base_code import BaseCode

class FailureCode(BaseCode):
    NOT_FOUND_DATA = ("존재하지 않는 데이터입니다", 404)
    BAD_REQUEST = ("잘못된 요청입니다", 400)
