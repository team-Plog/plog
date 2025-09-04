import re
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse
from datetime import datetime

import httpx
from collections import defaultdict
from sqlalchemy.orm import Session
from app.db.sqlite.models.project_models import OpenAPISpecModel, OpenAPISpecVersionModel, EndpointModel, ParameterModel
from app.dto.open_api_spec.open_api_spec_register_request import OpenAPISpecRegisterRequest
from app.services.openapi.analysis_strategy import OpenAPIAnalysisStrategy


def resolve_schema_references(schema: Dict[str, Any], components: Dict[str, Any], visited: set = None) -> Dict[str, Any]:
    """
    OpenAPI 스키마의 $ref 참조를 재귀적으로 해결하여 최종 JSON 형태로 변환
    
    Args:
        schema: 해결할 스키마 객체
        components: OpenAPI components 섹션
        visited: 순환 참조 방지를 위한 방문한 참조 목록
    
    Returns:
        $ref가 해결된 최종 스키마 객체
    """
    if visited is None:
        visited = set()
    
    if not isinstance(schema, dict):
        return schema
    
    # $ref 참조가 있는 경우
    if "$ref" in schema:
        ref_path = schema["$ref"]
        
        # 순환 참조 방지
        if ref_path in visited:
            return {"type": "object", "description": f"Circular reference to {ref_path}"}
        
        visited.add(ref_path)
        
        # #/components/schemas/SchemaName 형태의 참조 파싱
        if ref_path.startswith("#/components/schemas/"):
            schema_name = ref_path.split("/")[-1]
            if schema_name in components.get("schemas", {}):
                referenced_schema = components["schemas"][schema_name]
                # 재귀적으로 참조 해결
                resolved = resolve_schema_references(referenced_schema, components, visited.copy())
                visited.discard(ref_path)
                return resolved
        
        visited.discard(ref_path)
        return {"type": "object", "description": f"Unresolved reference: {ref_path}"}
    
    # 스키마 객체의 각 프로퍼티를 재귀적으로 처리
    resolved_schema = {}
    for key, value in schema.items():
        if key == "properties" and isinstance(value, dict):
            # properties 안의 각 속성도 재귀 처리
            resolved_schema[key] = {
                prop_name: resolve_schema_references(prop_schema, components, visited.copy())
                for prop_name, prop_schema in value.items()
            }
        elif key == "items" and isinstance(value, dict):
            # 배열의 items도 재귀 처리
            resolved_schema[key] = resolve_schema_references(value, components, visited.copy())
        elif isinstance(value, dict):
            # 다른 객체도 재귀 처리
            resolved_schema[key] = resolve_schema_references(value, components, visited.copy())
        elif isinstance(value, list):
            # 리스트 안의 객체들도 처리
            resolved_schema[key] = [
                resolve_schema_references(item, components, visited.copy()) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            resolved_schema[key] = value
    
    return resolved_schema


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
    
    async def analyze(self, request: OpenAPISpecRegisterRequest, db: Session = None) -> OpenAPISpecModel:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(str(request.open_api_url))
            response.raise_for_status()
            openapi_data = response.json()

        # 1. 기본 정보 추출
        title = openapi_data.get("info", {}).get("title", "Untitled")
        version = openapi_data.get("info", {}).get("version", "unknown")
        servers = openapi_data.get("servers", [])
        
        # base_url 결정 (servers가 없거나 비어있는 경우 요청 URL에서 파싱)
        if servers and isinstance(servers, list) and len(servers) > 0 and isinstance(servers[0], dict) and "url" in servers[0]:
            base_url = str(servers[0]["url"])
        else:
            # 요청 URL에서 base_url 파싱 (scheme://netloc 부분만 추출)
            parsed_url = urlparse(str(request.open_api_url))
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}" if parsed_url.scheme and parsed_url.netloc else str(request.open_api_url)

        # 2. 동일한 base_url을 가진 openapi_spec이 존재하는지 확인
        existing_spec = None
        if db:
            existing_spec = db.query(OpenAPISpecModel).filter(
                OpenAPISpecModel.base_url == base_url,
                OpenAPISpecModel.project_id == request.project_id
            ).first()
        
        # 존재하면 기존 것을 사용, 없으면 새로 생성
        if existing_spec:
            openapi_spec_model = existing_spec
        else:
            openapi_spec_model = OpenAPISpecModel(
                title=title,
                version=version,
                base_url=base_url,
                project_id=request.project_id,
            )
        
        # 3. OpenAPI 스펙 버전 생성
        if db and existing_spec:
            # 기존 버전들을 모두 비활성화
            db.query(OpenAPISpecVersionModel).filter(
                OpenAPISpecVersionModel.open_api_spec_id == existing_spec.id
            ).update({"is_activate": False})
        
        openapi_spec_version = OpenAPISpecVersionModel(
            created_at=datetime.now(),
            commit_hash=getattr(request, 'commit_hash', None),
            is_activate=True,
            open_api_spec_id=openapi_spec_model.id if existing_spec else None
        )

        # 4. tag description 매핑
        tag_defs = {tag["name"]: tag.get("description", "") for tag in openapi_data.get("tags", [])}

        # 5. endpoint 저장 & 파라미터 파싱 (반정규화된 구조)
        all_endpoints = []
        components = openapi_data.get("components", {})

        paths = openapi_data.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                # 태그 정보 처리 (첫 번째 태그 사용, 없으면 Default)
                tags = details.get("tags", ["Default"])
                primary_tag = tags[0] if tags else "Default"
                tag_description = tag_defs.get(primary_tag, "")
                
                endpoint_model = EndpointModel(
                    path=path,
                    method=method.upper(),
                    summary=details.get("summary", ""),
                    description=details.get("description", ""),
                    tag_name=primary_tag,
                    tag_description=tag_description,
                    openapi_spec_version_id=None  # 나중에 설정
                )
                
                # 파라미터 파싱
                parameters = []
                
                # Path & Query parameters
                for param in details.get("parameters", []):
                    param_type = param.get("in", "")
                    if param_type in ["path", "query"]:
                        schema = param.get("schema", {})
                        parameter_model = ParameterModel(
                            param_type=param_type,
                            name=param.get("name", ""),
                            required=param.get("required", False),
                            value_type=schema.get("type", ""),
                            title=schema.get("title", ""),
                            description=param.get("description", ""),
                            value=schema.get("default")  # 기본값이 있으면 저장
                        )
                        parameters.append(parameter_model)
                
                # Request Body parameter
                request_body = details.get("requestBody")
                if request_body:
                    content = request_body.get("content", {})
                    # application/json 우선 처리
                    json_content = content.get("application/json", {})
                    if json_content:
                        schema = json_content.get("schema", {})
                        # 스키마 참조 해결
                        resolved_schema = resolve_schema_references(schema, components)
                        
                        parameter_model = ParameterModel(
                            param_type="requestBody",
                            name="requestBody",
                            required=request_body.get("required", False),
                            value_type="object",
                            title="Request Body",
                            description=request_body.get("description", ""),
                            value=resolved_schema
                        )
                        parameters.append(parameter_model)
                
                # endpoint에 파라미터 연결
                endpoint_model.parameters = parameters
                all_endpoints.append(endpoint_model)

        # endpoints를 openapi_spec_version에 연결
        for endpoint in all_endpoints:
            endpoint.openapi_spec_version = openapi_spec_version
        openapi_spec_version.endpoints = all_endpoints
        
        # openapi_spec_version을 openapi_spec에 연결
        if not existing_spec:
            openapi_spec_model.openapi_spec_versions = [openapi_spec_version]
        else:
            openapi_spec_model.openapi_spec_versions.append(openapi_spec_version)

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

    async def analyze(self, request: OpenAPISpecRegisterRequest, db: Session = None) -> OpenAPISpecModel:
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

        # 동일한 base_url을 가진 openapi_spec이 존재하는지 확인
        existing_spec = None
        if db:
            existing_spec = db.query(OpenAPISpecModel).filter(
                OpenAPISpecModel.base_url == base_url,
                OpenAPISpecModel.project_id == request.project_id
            ).first()
        
        # 존재하면 기존 것을 사용, 없으면 새로 생성
        if existing_spec:
            openapi_spec_model = existing_spec
        else:
            openapi_spec_model = OpenAPISpecModel(
                title=title,
                version=version,
                base_url=base_url,
                project_id=request.project_id,
            )
        
        # OpenAPI 스펙 버전 생성
        if db and existing_spec:
            # 기존 버전들을 모두 비활성화
            db.query(OpenAPISpecVersionModel).filter(
                OpenAPISpecVersionModel.open_api_spec_id == existing_spec.id
            ).update({"is_activate": False})
        
        openapi_spec_version = OpenAPISpecVersionModel(
            created_at=datetime.now(),
            commit_hash=getattr(request, 'commit_hash', None),
            is_activate=True,
            open_api_spec_id=openapi_spec_model.id if existing_spec else None
        )

        # 태그 설명 맵 결합
        tag_defs: Dict[str, str] = {}
        for spec in openapi_data_list:
            for t in spec.get("tags", []) or []:
                name = t.get("name")
                if name and name not in tag_defs:
                    tag_defs[name] = t.get("description", "") or ""

        # 엔드포인트 & 파라미터 파싱 (반정규화된 구조)
        all_endpoints: List[EndpointModel] = []

        for spec in openapi_data_list:
            components = spec.get("components", {})
            paths = spec.get("paths", {}) or {}
            for path, methods in paths.items():
                if not isinstance(methods, dict):
                    continue
                for method, details in methods.items():
                    if not isinstance(details, dict):
                        continue
                    
                    # 태그 정보 처리 (첫 번째 태그 사용, 없으면 Default)
                    tags = details.get("tags") or ["Default"]
                    primary_tag = tags[0] if tags else "Default"
                    tag_description = tag_defs.get(primary_tag, "")
                    
                    endpoint_model = EndpointModel(
                        path=path,
                        method=str(method).upper(),
                        summary=details.get("summary", "") or "",
                        description=details.get("description", "") or "",
                        tag_name=primary_tag,
                        tag_description=tag_description,
                        openapi_spec_version_id=None  # 나중에 설정
                    )
                    
                    # 파라미터 파싱
                    parameters = []
                    
                    # Path & Query parameters
                    for param in details.get("parameters", []):
                        if not isinstance(param, dict):
                            continue
                        param_type = param.get("in", "")
                        if param_type in ["path", "query"]:
                            schema = param.get("schema", {})
                            parameter_model = ParameterModel(
                                param_type=param_type,
                                name=param.get("name", ""),
                                required=param.get("required", False),
                                value_type=schema.get("type", ""),
                                title=schema.get("title", ""),
                                description=param.get("description", ""),
                                value=schema.get("default")  # 기본값이 있으면 저장
                            )
                            parameters.append(parameter_model)
                    
                    # Request Body parameter
                    request_body = details.get("requestBody")
                    if request_body and isinstance(request_body, dict):
                        content = request_body.get("content", {})
                        # application/json 우선 처리
                        json_content = content.get("application/json", {})
                        if json_content:
                            schema = json_content.get("schema", {})
                            # 스키마 참조 해결
                            resolved_schema = resolve_schema_references(schema, components)
                            
                            parameter_model = ParameterModel(
                                param_type="requestBody",
                                name="requestBody",
                                required=request_body.get("required", False),
                                value_type="object",
                                title="Request Body",
                                description=request_body.get("description", ""),
                                value=resolved_schema
                            )
                            parameters.append(parameter_model)
                    
                    # endpoint에 파라미터 연결
                    endpoint_model.parameters = parameters
                    all_endpoints.append(endpoint_model)

        # endpoints를 openapi_spec_version에 연결
        for endpoint in all_endpoints:
            endpoint.openapi_spec_version = openapi_spec_version
        openapi_spec_version.endpoints = all_endpoints
        
        # openapi_spec_version을 openapi_spec에 연결
        if not existing_spec:
            openapi_spec_model.openapi_spec_versions = [openapi_spec_version]
        else:
            openapi_spec_model.openapi_spec_versions.append(openapi_spec_version)

        return openapi_spec_model