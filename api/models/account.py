from pydantic import BaseModel

class Account(BaseModel):
    id: str
    balance: str
