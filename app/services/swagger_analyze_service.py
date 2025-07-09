import httpx
from collections import defaultdict
from app.db.sqlite.models import OpenAPISpecModel, EndpointModel, TagModel

async def analyze_openapi_spec(swagger_url: str) -> OpenAPISpecModel:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(swagger_url)
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
        tag_model.openapi_spec=openapi_spec_model
        tag_model.endpoints=endpoint_models

        tag_models.append(tag_model)

    return openapi_spec_model
