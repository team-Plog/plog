from pydantic import BaseModel
from typing import List, Optional


class Endpoint(BaseModel):
    path: str
    method: str
    summary: Optional[str]
    description: Optional[str]

    class Config:
        from_attributes = True

class OpenAPISpec(BaseModel):
    title: str
    version: str
    endpoints: List[Endpoint]

    class Config:
        from_attributes = True