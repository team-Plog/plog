from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from app.dto.open_api_spec.parsed_open_api_spec import ParsedOpenAPISpec


class OpenAPIParser(ABC):
    """OpenAPI 파싱 인터페이스"""

    @abstractmethod
    async def fetch_spec(self, url: str) -> Dict[str, Any]:
        """OpenAPI 스펙 데이터를 가져옴"""
        pass

    @abstractmethod
    def parse_spec(self, data: Dict[str, Any]) -> ParsedOpenAPISpec:
        """OpenAPI 스펙을 파싱"""
        pass