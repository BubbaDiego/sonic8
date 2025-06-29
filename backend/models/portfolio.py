from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import uuid4

class PortfolioSnapshot(BaseModel):
    """Represents an aggregate view of portfolio metrics at a specific time."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the snapshot",
    )
    snapshot_time: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of the portfolio snapshot",
    )
    total_size: float = Field(..., description="Total size of all positions")
    total_value: float = Field(..., description="Total value of the portfolio")
    total_collateral: float = Field(
        ..., description="Total collateral provided for the portfolio"
    )
    avg_leverage: float = Field(
        ..., description="Average leverage across all positions"
    )
    avg_travel_percent: float = Field(
        ..., description="Average travel percent to liquidation across positions"
    )
    avg_heat_index: float = Field(
        ..., description="Average heat index reflecting portfolio risk"
    )

    class Config:
        orm_mode = True

