from typing import Dict, Any, Optional

import httpx

from app.business.openapi.open_api_parser import OpenAPIParser
from app.common.exception.api_exception import ApiException
from app.common.response.code import FailureCode
from app.dto.open_api_spec.parsed_open_api_spec import ParsedOpenAPISpec


class OpenApiParserApiDocs(OpenAPIParser):
    async def fetch_spec(self, url: str) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                    follow_redirects=True,
                    timeout=httpx.Timeout(30.0)
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            raise ApiException(e.response.status_code, e.response.json()) from e
        except Exception as e:
            raise ApiException(FailureCode.INTERNAL_SERVER_ERROR)


    def parse_spec(self, data: Dict[str, Any]) -> ParsedOpenAPISpec:
        # 1. 기본 정보 추출
        info = data.get("info", {})
        title = info.get("title", "Untitled")
        version = info.get("version", "1.0.0")
        description = info.get("description", "")
        base_url = data.get("servers", [])[0].get("url")



        ParsedOpenAPISpec(
            title=title,
            version=version,
            base_url=base_url,

        )