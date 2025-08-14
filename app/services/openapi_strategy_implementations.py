import re
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse

import httpx
from collections import defaultdict
from app.db.sqlite.models.project_models import OpenAPISpecModel, EndpointModel, TagModel
from app.dto.open_api_spec.open_api_spec_register_request import OpenAPISpecRegisterRequest
from app.services.openapi_analysis_strategy import OpenAPIAnalysisStrategy


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
    
    async def analyze(self, request: OpenAPISpecRegisterRequest) -> OpenAPISpecModel:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(str(request.open_api_url))
            response.raise_for_status()
            openapi_data = response.json()

        # 1. 기본 정보 추출
        title = openapi_data.get("info", {}).get("title", "Untitled")
        version = openapi_data.get("info", {}).get("version", "unknown")
        servers = openapi_data.get("servers", [])
        base_url = servers[0]["url"]

        # 2. openapi 스펙 모델 생성
        openapi_spec_model = OpenAPISpecModel(
            title=title,
            version=version,
            base_url=base_url,
            project_id=request.project_id,
        )

        # 3. tag description 매핑
        tag_defs = {tag["name"]: tag.get("description", "") for tag in openapi_data.get("tags", [])}

        # 4. endpoint 저장 & 태그 분류
        tag_map = defaultdict(list)
        all_endpoints = []  # DB에 들어갈 endpoint들

        paths = openapi_data.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                endpoint_model = EndpointModel(
                    path=path,
                    method=method.upper(),
                    summary=details.get("summary", ""),
                    description=details.get("description", "")
                )
                all_endpoints.append(endpoint_model)

                tags = details.get("tags", ["Default"])
                for tag in tags:
                    tag_map[tag].append(endpoint_model)

        # 5. tag 모델 생성 + 연결
        tag_models = []
        for tag_name, endpoint_models in tag_map.items():
            tag_model = TagModel(
                name=tag_name,
                description=tag_defs.get(tag_name, ""),
            )
            # 연관관계 매핑
            tag_model.openapi_spec = openapi_spec_model
            tag_model.endpoints = endpoint_models

            tag_models.append(tag_model)

        return openapi_spec_model


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

    async def analyze(self, request: OpenAPISpecRegisterRequest) -> OpenAPISpecModel:
        """
        Swagger UI에서 OpenAPI 스펙 URL을 찾아 파싱.
        - data-url
        - SwaggerUIBundle({ url }) / ({ urls: [...] })
        - swagger-initializer.js
        - 마지막 수단: 동일 오리진 + /v3/api-docs 추정
        """
        swagger_ui_url = str(request.open_api_url)

        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            # 0) HTML 로드
            resp = await client.get(swagger_ui_url)
            resp.raise_for_status()
            html = resp.text

            spec_urls: List[str] = []

            # A) data-url 속성
            m_data = re.search(r'id=["\']swagger-ui["\'][^>]*\bdata-url=["\']([^"\']+)["\']', html, re.I)
            if m_data:
                spec_urls.append(urljoin(swagger_ui_url, m_data.group(1)))

            # B) HTML에서 SwaggerUIBundle 설정 (단일 url)
            for m in re.finditer(r'SwaggerUIBundle\(\s*\{(.*?)\}\s*\)', html, re.S):
                block = m.group(1)
                for ms in re.finditer(r'\burl\s*:\s*["\']([^"\']+)["\']', block):
                    spec_urls.append(urljoin(swagger_ui_url, ms.group(1)))
                # urls 배열
                for mu in re.finditer(r'\burls\s*:\s*\[(.*?)\]', block, re.S):
                    blk = mu.group(1)
                    for mx in re.finditer(r'\burl\s*:\s*["\']([^"\']+)["\']', blk):
                        spec_urls.append(urljoin(swagger_ui_url, mx.group(1)))

            # C) initializer.js를 찾아서 동일 로직 적용 (예외 처리 포함)
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

            # D) 후보 정리/랭킹
            ranked = self._rank_spec_candidates(spec_urls, swagger_ui_url)

            # E) 없으면 /v3/api-docs 추정
            if not ranked:
                parsed = urlparse(swagger_ui_url)
                guess = f"{parsed.scheme}://{parsed.netloc}/v3/api-docs"
                ranked = [guess]

            # 스펙들 로드 (강화된 오류 처리)
            openapi_data_list: List[Dict[str, Any]] = []
            for spec_url in ranked:
                try:
                    r = await client.get(spec_url)
                    r.raise_for_status()
                    data = r.json()
                    # 최소 요건 체크
                    if isinstance(data, dict) and ("openapi" in data or "swagger" in data):
                        openapi_data_list.append(data)
                except httpx.HTTPStatusError as e:
                    # HTTP 상태 오류는 로그로 기록하고 다음 URL 시도
                    continue
                except (httpx.RequestError, ValueError) as e:
                    # 연결 오류나 JSON 파싱 오류는 다음 URL 시도  
                    continue
                except Exception:
                    # 기타 예외도 다음 URL 시도
                    continue

            if not openapi_data_list:
                # 더 구체적인 오류 메시지 제공
                if len(ranked) == 1 and ranked[0].endswith('/v3/api-docs'):
                    raise ValueError(f"Swagger UI에서 OpenAPI 스펙을 찾을 수 없습니다. {swagger_ui_url}에서 스펙 URL을 확인할 수 없고, 기본 경로({ranked[0]})도 접근할 수 없습니다.")
                else:
                    raise ValueError(f"Swagger UI에서 유효한 OpenAPI 스펙을 가져오지 못했습니다. 시도한 URL: {', '.join(ranked)}")

        # 기본 정보(첫 스펙 기준)
        primary = openapi_data_list[0]
        title = primary.get("info", {}).get("title", "Untitled")
        version = primary.get("info", {}).get("version", "unknown")

        # base_url 결정
        def pick_base_url(spec_json: Dict[str, Any], fallback_url: str) -> str:
            servers = spec_json.get("servers", [])
            if servers and isinstance(servers, list) and isinstance(servers[0], dict) and "url" in servers[0]:
                return str(servers[0]["url"])
            p = urlparse(fallback_url)
            return f"{p.scheme}://{p.netloc}" if p.scheme and p.netloc else fallback_url

        base_url = pick_base_url(primary, ranked[0] if ranked else swagger_ui_url)

        # OpenAPISpecModel 구성
        openapi_spec_model = OpenAPISpecModel(
            title=title,
            version=version,
            base_url=base_url,
            project_id=request.project_id,
        )

        # 태그 설명 맵 결합
        tag_defs: Dict[str, str] = {}
        for spec in openapi_data_list:
            for t in spec.get("tags", []) or []:
                name = t.get("name")
                if name and name not in tag_defs:
                    tag_defs[name] = t.get("description", "") or ""

        # 엔드포인트/태그
        tag_map = defaultdict(list)
        all_endpoints: List[EndpointModel] = []

        for spec in openapi_data_list:
            paths = spec.get("paths", {}) or {}
            for path, methods in paths.items():
                if not isinstance(methods, dict):
                    continue
                for method, details in methods.items():
                    if not isinstance(details, dict):
                        continue
                    endpoint_model = EndpointModel(
                        path=path,
                        method=str(method).upper(),
                        summary=details.get("summary", "") or "",
                        description=details.get("description", "") or ""
                    )
                    all_endpoints.append(endpoint_model)

                    tags = details.get("tags") or ["Default"]
                    for tag in tags:
                        tag_map[tag].append(endpoint_model)

        # 태그 모델 매핑
        tag_models: List[TagModel] = []
        for tag_name, endpoint_models in tag_map.items():
            tag_model = TagModel(
                name=tag_name,
                description=tag_defs.get(tag_name, ""),
            )
            tag_model.openapi_spec = openapi_spec_model
            tag_model.endpoints = endpoint_models
            tag_models.append(tag_model)

        return openapi_spec_model