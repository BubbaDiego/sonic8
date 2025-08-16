from pydantic import BaseModel


class Position(BaseModel):
    id: str
    instrument: str
    qty: str
    account_id: str


class PositionAdjustRequest(BaseModel):
    delta: str
