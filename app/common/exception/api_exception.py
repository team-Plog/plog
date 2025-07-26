from app.common.response.code.base_code import BaseCode

class ApiException(Exception):
    def __init__(self, code: BaseCode, message: str = None):
        self.code = code
        self.message = message or code.message()
        super().__init__(self.code)