from pydantic import BaseModel

class ConnectOpenAPIInfraRequest(BaseModel):
    openapi_spec_id: int
    group_name: str