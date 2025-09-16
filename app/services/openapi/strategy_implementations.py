import re
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse

import httpx
from app.dto.openapi_parse_result import OpenAPIParseResult
from app.schemas.openapi_spec.open_api_spec_register_request import OpenAPISpecRegisterRequest
from app.services.openapi.analysis_strategy import OpenAPIAnalysisStrategy
from app.services.openapi.endpoint_parser import (
    extract_tag_definitions,
    parse_endpoints_from_openapi,
    determine_base_url_from_openapi
)



class DirectOpenAPIStrategy(OpenAPIAnalysisStrategy):
    """직접 OpenAPI JSON URL을 분석하는 전략 (Singleton)"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialized = True
    
    async def parse(self, request: OpenAPISpecRegisterRequest) -> OpenAPIParseResult:
        """
        직접 OpenAPI JSON URL에서 스펙을 파싱합니다.

        Args:
            request: OpenAPI 스펙 등록 요청 객체

        Returns:
            OpenAPIParseResult: 파싱된 OpenAPI 스펙 데이터
        """
        # 1. HTTP 요청으로 OpenAPI 데이터 가져오기
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(str(request.open_api_url))
            response.raise_for_status()
            openapi_data = response.json()

        # 2. 기본 정보 추출
        title = openapi_data.get("info", {}).get("title", "Untitled")
        version = openapi_data.get("info", {}).get("version", "unknown")

        # 3. base_url 결정
        base_url = determine_base_url_from_openapi(openapi_data, str(request.open_api_url))

        # 4. 태그 정의 추출
        tag_definitions = extract_tag_definitions([openapi_data])

        # 5. 엔드포인트 파싱
        endpoints = parse_endpoints_from_openapi([openapi_data], tag_definitions)

        return OpenAPIParseResult(
            title=title,
            version=version,
            base_url=base_url,
            endpoints=endpoints,
            tag_definitions=tag_definitions,
            raw_openapi_data=openapi_data
        )


class SwaggerUIStrategy(OpenAPIAnalysisStrategy):
    """Swagger UI 페이지에서 OpenAPI 스펙을 찾아 분석하는 전략 (Singleton)"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialized = True
    
    def _same_origin(self, u1: str, u2: str) -> bool:
        p1, p2 = urlparse(u1), urlparse(u2)
        return (p1.scheme, p1.netloc) == (p2.scheme, p2.netloc)

    def _rank_spec_candidates(self, cands: List[str], swagger_ui_url: str) -> List[str]:
        """동일 오리진 우선, 스펙 패턴 우선, petstore/예제 도메인 제외"""
        bad_domains = ("petstore.swagger.io", "example.com")
        # 제외 먼저
        cands = [c for c in cands if urlparse(c).netloc not in bad_domains]

        def score(u: str) -> int:
            s = 0
            if self._same_origin(u, swagger_ui_url): s += 10
            path = urlparse(u).path.lower()
            if "/v3/api-docs" in path: s += 5
            if path.endswith(("/swagger.json", "/openapi.json")): s += 5
            return s

        return sorted(set(cands), key=lambda x: (-score(x), x))

    async def parse(self, request: OpenAPISpecRegisterRequest) -> OpenAPIParseResult:
        """
        Swagger UI에서 OpenAPI 스펙 URL을 찾아 파싱합니다.
        - data-url 속성 검색
        - SwaggerUIBundle 설정 검색
        - swagger-initializer.js 검색
        - 마지막 수단: /v3/api-docs 추정

        Args:
            request: OpenAPI 스펙 등록 요청 객체

        Returns:
            OpenAPIParseResult: 파싱된 OpenAPI 스펙 데이터
        """
        swagger_ui_url = str(request.open_api_url)

        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            # 1. HTML 로드
            resp = await client.get(swagger_ui_url)
            resp.raise_for_status()
            html = resp.text

            spec_urls: List[str] = []

            # 2. data-url 속성 검색
            m_data = re.search(r'id=["\']swagger-ui["\'][^>]*\bdata-url=["\']([^"\']+)["\']', html, re.I)
            if m_data:
                spec_urls.append(urljoin(swagger_ui_url, m_data.group(1)))

            # 3. SwaggerUIBundle 설정 검색
            for m in re.finditer(r'SwaggerUIBundle\(\s*\{(.*?)\}\s*\)', html, re.S):
                block = m.group(1)
                for ms in re.finditer(r'\burl\s*:\s*["\']([^"\']+)["\']', block):
                    spec_urls.append(urljoin(swagger_ui_url, ms.group(1)))
                # urls 배열
                for mu in re.finditer(r'\burls\s*:\s*\[(.*?)\]', block, re.S):
                    blk = mu.group(1)
                    for mx in re.finditer(r'\burl\s*:\s*["\']([^"\']+)["\']', blk):
                        spec_urls.append(urljoin(swagger_ui_url, mx.group(1)))

            # 4. swagger-initializer.js 검색
            if not spec_urls:
                m_src = re.search(r'<script[^>]+src=["\']([^"\']*swagger[^"\']*initializer[^"\']*)["\']', html, re.I)
                if m_src:
                    init_js_url = urljoin(swagger_ui_url, m_src.group(1))
                    try:
                        js_resp = await client.get(init_js_url)
                        js_resp.raise_for_status()
                        init_js = js_resp.text
                        for m in re.finditer(r'SwaggerUIBundle\(\s*\{(.*?)\}\s*\)', init_js, re.S):
                            block = m.group(1)
                            for ms in re.finditer(r'\burl\s*:\s*["\']([^"\']+)["\']', block):
                                spec_urls.append(urljoin(init_js_url, ms.group(1)))
                            for mu in re.finditer(r'\burls\s*:\s*\[(.*?)\]', block, re.S):
                                blk = mu.group(1)
                                for mx in re.finditer(r'\burl\s*:\s*["\']([^"\']+)["\']', blk):
                                    spec_urls.append(urljoin(init_js_url, mx.group(1)))
                    except Exception:
                        # swagger-initializer.js 접근 실패 시 다음 단계로 진행
                        pass

            # 5. 후보 정리/랭킹
            ranked = self._rank_spec_candidates(spec_urls, swagger_ui_url)

            # 6. 없으면 /v3/api-docs 추정
            if not ranked:
                parsed = urlparse(swagger_ui_url)
                guess = f"{parsed.scheme}://{parsed.netloc}/v3/api-docs"
                ranked = [guess]

            # 7. 스펙들 로드 (강화된 오류 처리)
            openapi_data_list: List[Dict[str, Any]] = []
            for spec_url in ranked:
                try:
                    r = await client.get(spec_url)
                    r.raise_for_status()
                    data = r.json()
                    # 최소 요건 체크
                    if isinstance(data, dict) and ("openapi" in data or "swagger" in data):
                        openapi_data_list.append(data)
                except (httpx.HTTPStatusError, httpx.RequestError, ValueError, Exception):
                    # 모든 오류는 다음 URL 시도
                    continue

            if not openapi_data_list:
                # 구체적인 오류 메시지 제공
                if len(ranked) == 1 and ranked[0].endswith('/v3/api-docs'):
                    raise ValueError(f"Swagger UI에서 OpenAPI 스펙을 찾을 수 없습니다. {swagger_ui_url}에서 스펙 URL을 확인할 수 없고, 기본 경로({ranked[0]})도 접근할 수 없습니다.")
                else:
                    raise ValueError(f"Swagger UI에서 유효한 OpenAPI 스펙을 가져오지 못했습니다. 시도한 URL: {', '.join(ranked)}")

        # 8. 기본 정보 추출 (첫 스펙 기준)
        primary = openapi_data_list[0]
        title = primary.get("info", {}).get("title", "Untitled")
        version = primary.get("info", {}).get("version", "unknown")

        # 9. base_url 결정
        base_url = determine_base_url_from_openapi(primary, ranked[0] if ranked else swagger_ui_url)

        # 10. 태그 정의 추출 (모든 스펙 합쳐서)
        tag_definitions = extract_tag_definitions(openapi_data_list)

        # 11. 엔드포인트 파싱 (모든 스펙 합쳐서)
        endpoints = parse_endpoints_from_openapi(openapi_data_list, tag_definitions)

        return OpenAPIParseResult(
            title=title,
            version=version,
            base_url=base_url,
            endpoints=endpoints,
            tag_definitions=tag_definitions,
            raw_openapi_data=primary  # 첫 번째 스펙을 대표로 저장
        )