from pydantic import BaseModel

class Signal(BaseModel):
    id: str
    type: str
