from enum import Enum

class BaseCode(Enum):
    def message(self) -> str:
        return self.value[0]

    def status_code(self) -> int:
        return self.value[1]
