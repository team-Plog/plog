from typing import Dict, List, Any

from pydantic import BaseModel, Field, HttpUrl, validator

class ParsedOpenAPISpec(BaseModel):
    """파싱된 OpenAPI 스펙 데이터"""
    title: str
    version: str
    base_url: str
    tags: List['ParsedTag']
    endpoints: List['ParsedEndpoint']

class ParsedTag(BaseModel):
    name: str
    description: str

class ParsedEndpoint(BaseModel):
    """파싱된 엔드포인트 데이터"""
    path: str
    method: str
    summary: str
    description: str
    tags: List[str]