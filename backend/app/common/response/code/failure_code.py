from app.common.response.code.base_code import BaseCode

class FailureCode(BaseCode):
    INTERNAL_SERVER_ERROR = ("서버 에러입니다.", 500)
    NOT_FOUND_DATA = ("존재하지 않는 데이터입니다", 404)
    BAD_REQUEST = ("잘못된 요청입니다", 400)
