from pydantic import BaseModel
from typing import Optional

class OrderCreate(BaseModel):
    instrument: str
    side: str
    type: str
    qty: str
    price: Optional[str] = None
    account_id: str
    client_ref: Optional[str] = None

class Order(BaseModel):
    id: str
    instrument: str
    side: str
    type: str
    qty: str
    price: Optional[str] = None
    status: str = "open"
    account_id: str
