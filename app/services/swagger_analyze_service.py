import httpx
from app.models.openapi import OpenAPISpec, Endpoint

async def analyze_openapi_spec(swagger_url: str) -> OpenAPISpec:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(swagger_url)
        response.raise_for_status()
        openapi_data = response.json()

    # 기본 정보 추출
    title = openapi_data.get("info", {}).get("title", "Untitled")
    version = openapi_data.get("info", {}).get("version", "unknown")

    # 경로들 파싱
    paths = openapi_data.get("paths", {})
    endpoints = []
    for path, methods in paths.items():
        for method, details in methods.items():
            endpoint = Endpoint(
                path=path,
                method=method.upper(),
                summary=details.get("summary", ""),
                description=details.get("description", "")
            )
            endpoints.append(endpoint)

    return OpenAPISpec(
        title=title,
        version=version,
        endpoints=endpoints
    )
