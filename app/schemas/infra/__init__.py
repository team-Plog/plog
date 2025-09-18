from pydantic import BaseModel

class ConnectOpenAPIInfraRequest(BaseModel):
    openapi_spec_id: int
    group_name: str

class UpdateServerInfraResourceUsageRequest(BaseModel):
    group_name: str
    cpu_request_millicores: str
    cpu_limit_millicores: str
    memory_request_millicores: str
    memory_limit_millicores: str
