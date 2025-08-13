import re
from urllib.parse import urlparse
from typing import Optional

from app.services.openapi_analysis_strategy import OpenAPIAnalysisStrategy, OpenAPIAnalysisContext
from app.services.openapi_strategy_implementations import DirectOpenAPIStrategy, SwaggerUIStrategy
from app.dto.open_api_spec.open_api_spec_register_request import OpenAPISpecRegisterRequest


class OpenAPIStrategyFactory:
    """URL 패턴에 따라 적절한 OpenAPI 분석 전략을 선택하는 팩토리 클래스"""
    
    @staticmethod
    def detect_strategy_type(url: str) -> str:
        """
        URL 패턴을 분석하여 사용할 전략 타입을 결정합니다.
        
        Args:
            url: 분석할 URL
            
        Returns:
            'direct' 또는 'swagger_ui'
        """
        parsed = urlparse(url.lower())
        path = parsed.path
        
        # JSON 파일 확장자나 API docs 패턴이 있으면 Direct 전략
        if any(pattern in path for pattern in [
            '/swagger.json',
            '/openapi.json', 
            '/api-docs.json',
            '/v3/api-docs',
            '/v2/api-docs',
            '/api/v1/swagger.json',
            '/api/v2/swagger.json',
            '/api/v3/swagger.json'
        ]):
            return 'direct'
            
        # swagger-ui, docs, documentation 등 UI 관련 패턴이 있으면 SwaggerUI 전략
        if any(pattern in path for pattern in [
            'swagger-ui',
            'swagger/ui',
            'api-docs',
            'docs/',
            'documentation',
            'redoc'
        ]):
            return 'swagger_ui'
            
        # 쿼리 파라미터 확인
        if parsed.query:
            query = parsed.query.lower()
            if 'swagger' in query or 'openapi' in query or 'docs' in query:
                return 'swagger_ui'
        
        # 기본값: Swagger UI 전략 (대부분의 경우 UI 페이지일 가능성이 높음)
        return 'swagger_ui'
    
    @staticmethod
    def create_strategy(strategy_type: str) -> OpenAPIAnalysisStrategy:
        """
        전략 타입에 따라 구체적인 전략 인스턴스를 생성합니다.
        
        Args:
            strategy_type: 'direct' 또는 'swagger_ui'
            
        Returns:
            OpenAPIAnalysisStrategy 구현체
        """
        if strategy_type == 'direct':
            return DirectOpenAPIStrategy()
        elif strategy_type == 'swagger_ui':
            return SwaggerUIStrategy()
        else:
            raise ValueError(f"지원하지 않는 전략 타입입니다: {strategy_type}")
    
    @staticmethod
    def create_context_for_request(request: OpenAPISpecRegisterRequest) -> OpenAPIAnalysisContext:
        """
        요청 객체를 기반으로 적절한 전략이 설정된 컨텍스트를 생성합니다.
        
        Args:
            request: OpenAPI 스펙 등록 요청 객체
            
        Returns:
            적절한 전략이 설정된 OpenAPIAnalysisContext
        """
        url = str(request.open_api_url)
        strategy_type = OpenAPIStrategyFactory.detect_strategy_type(url)
        strategy = OpenAPIStrategyFactory.create_strategy(strategy_type)
        return OpenAPIAnalysisContext(strategy)


# 편의를 위한 간단한 함수들
def create_openapi_analysis_context(request: OpenAPISpecRegisterRequest) -> OpenAPIAnalysisContext:
    """요청에 따른 OpenAPI 분석 컨텍스트를 생성합니다."""
    return OpenAPIStrategyFactory.create_context_for_request(request)


def analyze_openapi_with_strategy(request: OpenAPISpecRegisterRequest):
    """전략 패턴을 사용하여 OpenAPI를 분석합니다."""
    context = create_openapi_analysis_context(request)
    return context.analyze(request)