from pydantic import BaseModel

class Strategy(BaseModel):
    id: str
    name: str
