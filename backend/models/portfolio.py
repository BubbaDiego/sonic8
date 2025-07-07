from datetime import datetime
from typing import Optional
try:
    from pydantic import BaseModel, Field
    if not hasattr(BaseModel, "__fields__"):
        raise ImportError("stub")
except Exception:  # pragma: no cover - optional dependency or stub detected
    class BaseModel:
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

        def dict(self) -> dict:  # type: ignore[override]
            return self.__dict__

    def Field(default=None, **_):  # type: ignore
        return default
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
    total_heat_index: float = Field(
        0.0, description="Sum of heat index across all positions"
    )
    market_average_sp500: float = Field(
        0.0, description="S&P500 index value at snapshot time"
    )
    # --- Short Term Goal Metrics ---
    session_start_time: Optional[datetime] = Field(
        default=None,
        description="Time when the performance tracking session began",
    )
    session_start_value: float = Field(
        0.0, description="Portfolio value at the start of the session"
    )
    current_session_value: float = Field(
        0.0, description="Current portfolio value for the session"
    )
    session_goal_value: float = Field(
        0.0, description="Target portfolio value for the session"
    )
    session_performance_value: float = Field(
        0.0, description="Performance delta relative to the session start"
    )

    class Config:
        orm_mode = True

