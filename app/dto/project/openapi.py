from datetime import datetime

from pydantic import BaseModel
from typing import List, Optional, Any

class ProjectResponse(BaseModel):
    id: int
    title: str
    summary: str
    description: str
    status: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True  # pydantic v2 -> 기존 from_orm = True 와 동일
    }

class Parameter(BaseModel):
    id: int
    param_type: str  # path, query, requestBody
    name: str
    required: bool
    value_type: Optional[str]  # integer, string, array, object etc.
    title: Optional[str]
    description: Optional[str]
    value: Optional[Any]  # JSON 데이터

    class Config:
        from_attributes = True

class Endpoint(BaseModel):
    id: int
    path: str
    method: str
    summary: Optional[str]
    description: Optional[str]
    parameters: List[Parameter] = []  # 엔드포인트의 파라미터들

    class Config:
        from_attributes = True

class Tag(BaseModel):
    id: int
    name: str
    description: Optional[str]
    endpoints: List[Endpoint]  # 이 태그가 가지는 엔드포인트들

    class Config:
        from_attributes = True

class OpenAPISpec(BaseModel):
    id: int
    title: str
    version: str
    base_url: str
    tags: List[Tag]  # 이 명세가 가지는 태그들

    class Config:
        from_attributes = True
