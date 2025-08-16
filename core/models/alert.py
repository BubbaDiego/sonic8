from dataclasses import dataclass

@dataclass
class Alert:
    id: str
    position_id: str
    level: str = "warning"
