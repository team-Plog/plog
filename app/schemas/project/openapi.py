from datetime import datetime

from pydantic import BaseModel, Field
from typing import Optional, Any, List


class ProjectResponse(BaseModel):
    id: int
    title: str
    summary: str
    description: str
    status: Optional[str] = None
    updated_at: Optional[datetime] = None
    openapi_specs: List["OpenAPISpec"] = []

    model_config = {
        "from_attributes": True  # pydantic v2 -> 기존 from_orm = True 와 동일
    }

class OpenAPISpec(BaseModel):
    id: int
    title: Optional[str] = None
    version: Optional[str] = None
    base_url: str
    project_id: Optional[int] = None
    versions: List["OpenAPISpecVersion"] = Field(default=[], alias="openapi_spec_versions")

    model_config = {
        "from_attributes": True
    }

class OpenAPISpecVersion(BaseModel):
    id: int
    created_at: datetime
    commit_hash: Optional[str] = None  # nullable=True
    is_activate: bool
    open_api_spec_id: int  # 순환 참조 방지를 위해 객체 대신 ID만 사용
    endpoints: List["Endpoint"] = []

    model_config = {
        "from_attributes": True
    }

class Endpoint(BaseModel):
    id: int
    path: str
    method: str
    summary: str
    description: str
    tag_name: str
    tag_description: str
    openapi_spec_version_id: int  # 순환 참조 방지를 위해 ID만 사용
    parameters: List["Parameter"] = []

    model_config = {
        "from_attributes": True
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
    endpoint_id: Optional[int] = None  # 순환 참조 방지를 위해 ID만 사용

    model_config = {
        "from_attributes": True
    }
