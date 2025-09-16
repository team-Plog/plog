from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.dto.openapi_parse_result import OpenAPIParseResult
from app.schemas.openapi_spec.open_api_spec_register_request import OpenAPISpecRegisterRequest


class OpenAPIAnalysisStrategy(ABC):
    """OpenAPI 파싱을 위한 추상 전략 클래스"""

    @abstractmethod
    async def parse(self, request: OpenAPISpecRegisterRequest) -> OpenAPIParseResult:
        """
        OpenAPI 스펙을 파싱하여 OpenAPIParseResult를 반환합니다.

        Args:
            request: OpenAPI 스펙 등록 요청 객체

        Returns:
            OpenAPIParseResult: 파싱된 OpenAPI 스펙 데이터
        """
        pass


class OpenAPIAnalysisContext:
    """OpenAPI 파싱 전략을 실행하는 컨텍스트 클래스"""

    def __init__(self, strategy: OpenAPIAnalysisStrategy):
        self._strategy = strategy

    def set_strategy(self, strategy: OpenAPIAnalysisStrategy):
        """전략을 변경합니다."""
        self._strategy = strategy

    async def parse(self, request: OpenAPISpecRegisterRequest) -> OpenAPIParseResult:
        """현재 설정된 전략으로 OpenAPI 스펙을 파싱합니다."""
        return await self._strategy.parse(request)