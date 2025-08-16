from dataclasses import dataclass

@dataclass
class Position:
    id: str
    instrument: str
    qty: str
    account_id: str
