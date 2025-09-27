from pydantic import BaseModel

class RegisterProjectRequest(BaseModel):
    title: str
    summary: str
    description: str

    class Config:
        orm_mode = True