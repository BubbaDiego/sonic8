from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

try:
    from pydantic import BaseModel, Field
except Exception:  # fallback stub if pydantic isn't present
    class BaseModel:  # type: ignore
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

        def dict(self, *_, **__) -> dict:  # compatibility
            return self.__dict__

    def Field(default=None, **_):  # type: ignore
        return default


def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat()


class PriceAlert(BaseModel):
    """
    Combined config + state for a single price alert.

    rule_type:
      - "move_pct"      : percent move from anchor
      - "move_abs"      : dollar move from anchor
      - "price_target"  : crosses a fixed price

    direction:
      - "up", "down", "both"
      - "above", "below" (for price_target)
    """

    # identity / scope
    id: Optional[int] = None
    asset: str  # e.g. "SPX", "BTC", "ETH", "SOL"
    label: Optional[str] = None  # human label for UI/XCom

    # rule definition
    rule_type: str = "move_pct"
    direction: str = "both"  # "up", "down", "both", "above", "below"
    base_threshold_value: float  # percent / dollars / target price

    recurrence_mode: str = "single"  # "single", "reset", "ladder"
    cooldown_seconds: int = 0
    enabled: bool = True

    # anchor / recurrence state
    original_anchor_price: Optional[float] = None
    original_anchor_time: Optional[str] = None  # ISO

    current_anchor_price: Optional[float] = None
    current_anchor_time: Optional[str] = None  # ISO

    effective_threshold_value: Optional[float] = None
    armed: bool = True
    fired_count: int = 0

    # runtime telemetry
    last_state: Optional[str] = None  # "OK", "WARN", "BREACH", "DISARMED"
    last_price: Optional[float] = None
    last_move_abs: Optional[float] = None
    last_move_pct: Optional[float] = None
    last_distance_to_target: Optional[float] = None
    last_proximity_ratio: Optional[float] = None
    last_evaluated_at: Optional[str] = None
    last_triggered_at: Optional[str] = None
    last_reset_at: Optional[str] = None

    metadata: Optional[Dict[str, Any]] = None

    created_at: str = Field(default_factory=_utcnow_iso)
    updated_at: str = Field(default_factory=_utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        # Works for both real pydantic and fallback
        if hasattr(self, "model_dump"):
            return self.model_dump()
        return self.dict()


__all__ = ["PriceAlert"]
