from datetime import datetime

from pydantic import BaseModel
from typing import List, Optional

class ProjectResponse(BaseModel):
    id: int
    title: str
    description: str
    status: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True  # pydantic v2 -> 기존 from_orm = True 와 동일
    }

class Endpoint(BaseModel):
    id: int
    path: str
    method: str
    summary: Optional[str]
    description: Optional[str]

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
