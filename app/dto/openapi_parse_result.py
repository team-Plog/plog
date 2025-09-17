from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class EndpointData:
    """엔드포인트 정보를 담는 데이터 클래스"""
    path: str
    method: str
    summary: str
    description: str
    tag_name: str
    tag_description: str
    parameters: List[Dict[str, Any]]  # 해당 엔드포인트의 파라미터들


@dataclass
class OpenAPIParseResult:
    """
    OpenAPI 파싱 결과를 담는 DTO 클래스
    전략 패턴에서 순수 파싱 결과만을 반환하는 용도
    """
    title: str
    version: str
    base_url: str
    endpoints: List[EndpointData]
    tag_definitions: Dict[str, str]  # 태그 이름 → 설명 매핑
    raw_openapi_data: Dict[str, Any]  # 디버깅용 원본 OpenAPI 데이터

    def __post_init__(self):
        """데이터 검증 및 기본값 설정"""
        if not self.title:
            self.title = "Untitled"
        if not self.version:
            self.version = "unknown"
        if not self.base_url:
            raise ValueError("base_url은 필수입니다")
        if not isinstance(self.endpoints, list):
            self.endpoints = []
        if not isinstance(self.tag_definitions, dict):
            self.tag_definitions = {}
        if not isinstance(self.raw_openapi_data, dict):
            self.raw_openapi_data = {}

    def get_endpoint_count(self) -> int:
        """총 엔드포인트 개수 반환"""
        return len(self.endpoints)

    def get_tags(self) -> List[str]:
        """사용된 태그 목록 반환"""
        return list(set(endpoint.tag_name for endpoint in self.endpoints))

    def get_methods(self) -> List[str]:
        """사용된 HTTP 메서드 목록 반환"""
        return list(set(endpoint.method for endpoint in self.endpoints))