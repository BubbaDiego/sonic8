from pydantic import BaseModel

class LiquidationAlertRequest(BaseModel):
    position_id: str

class Alert(BaseModel):
    id: str
    position_id: str
    level: str = "warning"
