from dataclasses import dataclass
from typing import Optional

@dataclass
class Order:
    id: str
    instrument: str
    side: str
    type: str
    qty: str
    price: Optional[str] = None
    status: str = "open"
    account_id: str = ""
