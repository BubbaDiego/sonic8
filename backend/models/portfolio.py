# backend/models/position.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, constr

class Position(BaseModel):
    id: constr(min_length=1)
    asset_type: str
    position_type: str
    entry_price: float
    size: float
    leverage: float
    wallet_name: str
    last_updated: Optional[datetime] = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True
