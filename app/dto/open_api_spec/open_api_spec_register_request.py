from pydantic import BaseModel, HttpUrl

class OpenAPISpecRegisterRequest(BaseModel):
    project_id: int
    open_api_url: HttpUrl