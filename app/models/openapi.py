from pydantic import BaseModel
from typing import List, Optional

class Endpoint(BaseModel):
    path: str
    method: str
    summary: Optional[str]
    description: Optional[str]

    class Config:
        from_attributes = True

class Tag(BaseModel):
    name: str
    description: Optional[str]
    endpoints: List[Endpoint]  # 이 태그가 가지는 엔드포인트들

    class Config:
        from_attributes = True

class OpenAPISpec(BaseModel):
    title: str
    version: str
    tags: List[Tag]  # 이 명세가 가지는 태그들

    class Config:
        from_attributes = True
