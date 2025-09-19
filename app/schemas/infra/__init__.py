from typing import Optional

from pydantic import BaseModel

class ConnectOpenAPIInfraRequest(BaseModel):
    openapi_spec_id: int
    group_name: str

class UpdateServerInfraResourceUsageRequest(BaseModel):
    group_name: str
    replicas: int
    cpu_request_millicores: Optional[str] = None
    cpu_limit_millicores: Optional[str] = None
    memory_request_millicores: Optional[str] = None
    memory_limit_millicores: Optional[str] = None
