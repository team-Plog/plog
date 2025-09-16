import re
from urllib.parse import urlparse
from typing import Optional
import httpx

from app.services.openapi.analysis_strategy import OpenAPIAnalysisStrategy, OpenAPIAnalysisContext
from app.services.openapi.strategy_implementations import DirectOpenAPIStrategy, SwaggerUIStrategy
from app.schemas.openapi_spec.open_api_spec_register_request import OpenAPISpecRegisterRequest


class OpenAPIStrategyFactory:
    """URL 패턴에 따라 적절한 OpenAPI 분석 전략을 선택하는 팩토리 클래스 (Singleton 인스턴스 관리)"""
    
    # Singleton 전략 인스턴스들을 미리 생성하여 재사용
    _direct_strategy = None
    _swagger_ui_strategy = None
    
    # Singleton Context 인스턴스들을 미리 생성하여 재사용
    _direct_context = None
    _swagger_ui_context = None
    
    @classmethod
    def _get_direct_strategy(cls) -> 'DirectOpenAPIStrategy':
        """DirectOpenAPIStrategy Singleton 인스턴스 반환"""
        if cls._direct_strategy is None:
            cls._direct_strategy = DirectOpenAPIStrategy()
        return cls._direct_strategy
    
    @classmethod
    def _get_swagger_ui_strategy(cls) -> 'SwaggerUIStrategy':
        """SwaggerUIStrategy Singleton 인스턴스 반환"""
        if cls._swagger_ui_strategy is None:
            cls._swagger_ui_strategy = SwaggerUIStrategy()
        return cls._swagger_ui_strategy
    
    @classmethod
    def _get_direct_context(cls) -> OpenAPIAnalysisContext:
        """DirectOpenAPIStrategy가 설정된 Context Singleton 인스턴스 반환"""
        if cls._direct_context is None:
            cls._direct_context = OpenAPIAnalysisContext(cls._get_direct_strategy())
        return cls._direct_context
    
    @classmethod
    def _get_swagger_ui_context(cls) -> OpenAPIAnalysisContext:
        """SwaggerUIStrategy가 설정된 Context Singleton 인스턴스 반환"""
        if cls._swagger_ui_context is None:
            cls._swagger_ui_context = OpenAPIAnalysisContext(cls._get_swagger_ui_strategy())
        return cls._swagger_ui_context
    
    @staticmethod
    async def detect_strategy_type(url: str) -> str:
        """
        URL 패턴과 Content-Type을 분석하여 사용할 전략 타입을 결정합니다.
        
        Args:
            url: 분석할 URL
            
        Returns:
            'direct' 또는 'swagger_ui'
        """
        parsed = urlparse(url.lower())
        path = parsed.path
        
        # 1. URL 패턴 기반 우선 판단
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
        
        # 2. URL 패턴으로 판단 불가능한 경우 HEAD 요청으로 Content-Type 확인
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                response = await client.head(url)
                content_type = response.headers.get('content-type', '').lower()
                
                # JSON 응답이면 Direct 전략
                if any(ct in content_type for ct in ['application/json', 'application/x-yaml', 'text/yaml']):
                    return 'direct'
                    
        except Exception:
            # HEAD 요청 실패 시 기본값으로 처리
            pass
        
        # 기본값: Swagger UI 전략
        return 'swagger_ui'
    
    @classmethod
    def create_strategy(cls, strategy_type: str) -> OpenAPIAnalysisStrategy:
        """
        전략 타입에 따라 Singleton 전략 인스턴스를 반환합니다.
        
        Args:
            strategy_type: 'direct' 또는 'swagger_ui'
            
        Returns:
            OpenAPIAnalysisStrategy 구현체 (Singleton)
        """
        if strategy_type == 'direct':
            return cls._get_direct_strategy()
        elif strategy_type == 'swagger_ui':
            return cls._get_swagger_ui_strategy()
        else:
            raise ValueError(f"지원하지 않는 전략 타입입니다: {strategy_type}")
    
    @classmethod
    async def create_context_for_request(cls, request: OpenAPISpecRegisterRequest) -> OpenAPIAnalysisContext:
        """
        요청 객체를 기반으로 적절한 전략이 설정된 Singleton 컨텍스트를 반환합니다.
        
        Args:
            request: OpenAPI 스펙 등록 요청 객체
            
        Returns:
            적절한 전략이 설정된 OpenAPIAnalysisContext (Singleton)
        """
        url = str(request.open_api_url)
        strategy_type = await cls.detect_strategy_type(url)
        
        if strategy_type == 'direct':
            return cls._get_direct_context()
        elif strategy_type == 'swagger_ui':
            return cls._get_swagger_ui_context()
        else:
            raise ValueError(f"지원하지 않는 전략 타입입니다: {strategy_type}")


# 편의를 위한 간단한 함수들
async def create_openapi_analysis_context(request: OpenAPISpecRegisterRequest) -> OpenAPIAnalysisContext:
    """요청에 따른 OpenAPI 분석 컨텍스트를 생성합니다."""
    return await OpenAPIStrategyFactory.create_context_for_request(request)


async def analyze_openapi_with_strategy(
        request: OpenAPISpecRegisterRequest,
        db=None,
        convert_url=True,
        conversion_mappings=None
):
    """전략 패턴을 사용하여 OpenAPI를 분석합니다. (호환성을 위한 래퍼 함수)"""
    # openapi_service의 함수로 위임
    from app.services.openapi.openapi_service import analyze_openapi_with_strategy as service_analyze
    return await service_analyze(request, db, convert_url, conversion_mappings)