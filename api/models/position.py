from pydantic import BaseModel
from typing import Optional

class Position(BaseModel):
    id: str
    instrument: str
    qty: str
    account_id: str

class PositionAdjustRequest(BaseModel):
    delta: int
