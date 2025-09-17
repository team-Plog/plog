from typing import List, Dict, Any
from urllib.parse import urlparse
from app.dto.openapi_parse_result import EndpointData


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


def extract_tag_definitions(openapi_data_list: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    OpenAPI 데이터에서 태그 정의 추출

    Args:
        openapi_data_list: OpenAPI 스펙 데이터 리스트

    Returns:
        Dict: 태그 이름 → 설명 매핑
    """
    tag_definitions = {}

    for openapi_data in openapi_data_list:
        tags = openapi_data.get("tags", []) or []
        for tag in tags:
            if isinstance(tag, dict):
                name = tag.get("name")
                if name and name not in tag_definitions:
                    tag_definitions[name] = tag.get("description", "") or ""

    return tag_definitions


def parse_parameter_from_openapi(param: Dict[str, Any]) -> Dict[str, Any]:
    """
    OpenAPI parameter 객체를 파라미터 데이터로 변환

    Args:
        param: OpenAPI parameter 객체

    Returns:
        Dict: 파라미터 데이터
    """
    if not isinstance(param, dict):
        return {}

    param_type = param.get("in", "")
    if param_type not in ["path", "query"]:
        return {}

    schema = param.get("schema", {})
    return {
        "param_type": param_type,
        "name": param.get("name", ""),
        "required": param.get("required", False),
        "value_type": schema.get("type", ""),
        "title": schema.get("title", ""),
        "description": param.get("description", ""),
        "value": schema.get("default")  # 기본값이 있으면 저장
    }


def parse_request_body_parameter(request_body: Dict[str, Any], components: Dict[str, Any]) -> Dict[str, Any]:
    """
    OpenAPI requestBody를 파라미터 데이터로 변환

    Args:
        request_body: OpenAPI requestBody 객체
        components: OpenAPI components 섹션

    Returns:
        Dict: 파라미터 데이터
    """
    if not request_body or not isinstance(request_body, dict):
        return {}

    content = request_body.get("content", {})
    # application/json 우선 처리
    json_content = content.get("application/json", {})
    if not json_content:
        return {}

    schema = json_content.get("schema", {})
    # 스키마 참조 해결
    resolved_schema = resolve_schema_references(schema, components)

    return {
        "param_type": "requestBody",
        "name": "requestBody",
        "required": request_body.get("required", False),
        "value_type": "object",
        "title": "Request Body",
        "description": request_body.get("description", ""),
        "value": resolved_schema
    }


def parse_endpoints_from_openapi(openapi_data_list: List[Dict[str, Any]], tag_definitions: Dict[str, str]) -> List[EndpointData]:
    """
    OpenAPI 데이터에서 엔드포인트 정보 추출

    Args:
        openapi_data_list: OpenAPI 스펙 데이터 리스트
        tag_definitions: 태그 정의 매핑

    Returns:
        List[EndpointData]: 파싱된 엔드포인트 데이터 리스트
    """
    all_endpoints = []

    for openapi_data in openapi_data_list:
        components = openapi_data.get("components", {})
        paths = openapi_data.get("paths", {}) or {}

        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue

            for method, details in methods.items():
                if not isinstance(details, dict):
                    continue

                # 태그 정보 처리 (첫 번째 태그 사용, 없으면 Default)
                tags = details.get("tags") or ["Default"]
                primary_tag = tags[0] if tags else "Default"
                tag_description = tag_definitions.get(primary_tag, "")

                # 파라미터 파싱
                parameters = []

                # Path & Query parameters
                for param in details.get("parameters", []):
                    param_data = parse_parameter_from_openapi(param)
                    if param_data:
                        parameters.append(param_data)

                # Request Body parameter
                request_body = details.get("requestBody")
                if request_body:
                    request_body_param = parse_request_body_parameter(request_body, components)
                    if request_body_param:
                        parameters.append(request_body_param)

                endpoint_data = EndpointData(
                    path=path,
                    method=str(method).upper(),
                    summary=details.get("summary", "") or "",
                    description=details.get("description", "") or "",
                    tag_name=primary_tag,
                    tag_description=tag_description,
                    parameters=parameters
                )

                all_endpoints.append(endpoint_data)

    return all_endpoints


def determine_base_url_from_openapi(openapi_data: Dict[str, Any], fallback_url: str) -> str:
    """
    OpenAPI 스펙에서 base_url 결정

    Args:
        openapi_data: OpenAPI 스펙 데이터
        fallback_url: 서버 정보가 없을 때 사용할 대체 URL

    Returns:
        str: 결정된 base_url
    """
    servers = openapi_data.get("servers", [])

    # servers가 있고 유효한 경우
    if servers and isinstance(servers, list) and len(servers) > 0:
        server = servers[0]
        if isinstance(server, dict) and "url" in server:
            return str(server["url"])

    # 서버 정보가 없는 경우 fallback URL에서 base URL 추출
    parsed_url = urlparse(fallback_url)
    if parsed_url.scheme and parsed_url.netloc:
        return f"{parsed_url.scheme}://{parsed_url.netloc}"

    return fallback_url