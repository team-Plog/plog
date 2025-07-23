from pydantic import BaseModel

class RegisterProjectRequest(BaseModel):
    title: str
    description: str

    class Config:
        orm_mode = True