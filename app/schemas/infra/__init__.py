from pydantic import BaseModel

class ConnectOpenAPIInfraRequest(BaseModel):
    openapi_spec_id: int
    server_infra_id: int