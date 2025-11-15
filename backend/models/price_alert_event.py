"""Event log entries for price alerts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

# Same pydantic fallback pattern as other models
try:
    from pydantic import BaseModel, Field, constr, ConfigDict

    if not hasattr(BaseModel, "__fields__"):
        raise ImportError("stub")
except Exception:  # pragma: no cover
    class BaseModel:  # type: ignore[override]
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

        def model_dump(self) -> dict:  # type: ignore
            return self.__dict__

        def dict(self) -> dict:  # type: ignore[override]
            return self.__dict__

    def Field(default=None, **_):  # type: ignore
        return default

    def constr(*_, **__):  # type: ignore
        return str

    ConfigDict = dict  # type: ignore


class PriceAlertEvent(BaseModel):
    """
    Append-only history of what happened to price alerts.

    This backs the ``dl_price_alert_events`` table and is used by:
      - Market Core (writes events)
      - Market Console (reads recent history)
      - any future web dashboards.
    """

    id: constr(min_length=1)
    alert_id: constr(min_length=1)

    symbol: str  # e.g. "BTC", "ETH", "SOL", "SPX"

    # "breach", "warn", "skip_snooze", "reset", "rearm", "created", "updated", ...
    event_type: str

    # Monitor-style state snapshot: "OK" | "WARN" | "BREACH" | "SKIP"
    state_after: Optional[str] = None

    # Price context at the time of the event
    price_at_event: Optional[float] = None
    anchor_at_event: Optional[float] = None
    movement_value: Optional[float] = None
    movement_percent: Optional[float] = None
    threshold_value: Optional[float] = None

    # Copy of rule metadata (so history is still readable if rules change later)
    rule_type: Optional[str] = None
    direction: Optional[str] = None
    recurrence_mode: Optional[str] = None

    # Where did this event come from? (market_core / console / api / xcom_bridge)
    source: Optional[str] = None

    # Free-form detail (e.g. "global snooze active", "manual reset to original")
    note: Optional[str] = None

    # Optional summary of XCom delivery outcome for breach events
    channels_result: Optional[Dict[str, Any]] = None

    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    model_config = ConfigDict(from_attributes=True)


__all__ = ["PriceAlertEvent"]
