from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.db.sqlite.models.project_models import OpenAPISpecModel
from app.dto.open_api_spec.open_api_spec_register_request import OpenAPISpecRegisterRequest


class OpenAPIAnalysisStrategy(ABC):
    """OpenAPI 분석을 위한 추상 전략 클래스"""
    
    @abstractmethod
    async def analyze(self, request: OpenAPISpecRegisterRequest) -> OpenAPISpecModel:
        """
        OpenAPI 스펙을 분석하여 OpenAPISpecModel을 반환합니다.
        
        Args:
            request: OpenAPI 스펙 등록 요청 객체
            
        Returns:
            OpenAPISpecModel: 분석된 OpenAPI 스펙 모델
        """
        pass


class OpenAPIAnalysisContext:
    """OpenAPI 분석 전략을 실행하는 컨텍스트 클래스"""
    
    def __init__(self, strategy: OpenAPIAnalysisStrategy):
        self._strategy = strategy
    
    def set_strategy(self, strategy: OpenAPIAnalysisStrategy):
        """전략을 변경합니다."""
        self._strategy = strategy
    
    async def analyze(self, request: OpenAPISpecRegisterRequest) -> OpenAPISpecModel:
        """현재 설정된 전략으로 OpenAPI 스펙을 분석합니다."""
        return await self._strategy.analyze(request)