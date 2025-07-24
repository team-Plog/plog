from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class EndpointResponse(BaseModel):
    id: int
    path: Optional[str]
    method: Optional[str]
    summary: Optional[str]
    description: Optional[str]

    model_config = {
        "from_attributes": True
    }

class TagResponse(BaseModel):
    id: int
    name: Optional[str]
    description: Optional[str]
    endpoints: List[EndpointResponse] = []

    model_config = {
        "from_attributes": True
    }


class OpenAPISpecResponse(BaseModel):
    id: int
    title: Optional[str]
    version: Optional[str]
    base_url: str
    tags: List[TagResponse] = []

    model_config = {
        "from_attributes": True
    }


class ProjectDetailResponse(BaseModel):
    id: int
    title: str
    summary: str
    description: str
    openapi_specs: List[OpenAPISpecResponse] = []

    model_config = {
        "from_attributes": True
    }
