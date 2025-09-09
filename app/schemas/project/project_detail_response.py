from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

class ParameterResponse(BaseModel):
    id: int
    param_type: str  # path, query, requestBody
    name: str
    required: bool
    value_type: Optional[str]  # integer, string, array, object etc.
    title: Optional[str]
    description: Optional[str]
    value: Optional[Any]  # JSON 데이터

    model_config = {
        "from_attributes": True
    }

class EndpointResponse(BaseModel):
    id: int
    path: Optional[str]
    method: Optional[str]
    summary: Optional[str]
    description: Optional[str]
    parameters: Optional[List[ParameterResponse]] = []  # 엔드포인트의 파라미터들

    model_config = {
        "from_attributes": True
    }

class TagResponse(BaseModel):
    id: int
    name: Optional[str]
    description: Optional[str]
    endpoints: Optional[List[EndpointResponse]] = None

    model_config = {
        "from_attributes": True
    }


class OpenAPISpecResponse(BaseModel):
    id: int
    title: Optional[str]
    version: Optional[str]
    base_url: str
    tags: Optional[List[TagResponse]]

    model_config = {
        "from_attributes": True
    }


class ProjectDetailResponse(BaseModel):
    id: int
    title: str
    summary: str
    description: str
    openapi_specs: Optional[List[OpenAPISpecResponse]]

    model_config = {
        "from_attributes": True
    }
