from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

try:
    from pydantic import BaseModel, Field
except Exception:  # fallback stub
    class BaseModel:  # type: ignore
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

        def dict(self, *_, **__) -> dict:
            return self.__dict__

    def Field(default=None, **_):  # type: ignore
        return default


def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat()


class PriceAlertEvent(BaseModel):
    """
    Append-only history of price alert evaluations / transitions.

    event_type examples:
      - "created", "updated", "deleted"
      - "breach", "warn", "reset"
      - "xcom_sent", "xcom_skip"
    """

    id: Optional[str] = None
    alert_id: Optional[int] = None
    asset: str

    event_type: str  # "breach", "warn", ...

    state_after: Optional[str] = None  # "OK", "WARN", "BREACH", ...

    price_at_event: Optional[float] = None
    anchor_at_event: Optional[float] = None
    movement_value: Optional[float] = None
    movement_percent: Optional[float] = None
    threshold_value: Optional[float] = None

    rule_type: Optional[str] = None
    direction: Optional[str] = None
    recurrence_mode: Optional[str] = None

    source: Optional[str] = None  # "market_core", "console", "api", "xcom"
    note: Optional[str] = None

    # JSON-encoded channels summary for breach events (optional)
    channels_result: Optional[Dict[str, Any]] = None

    created_at: str = Field(default_factory=_utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        if hasattr(self, "model_dump"):
            return self.model_dump()
        return self.dict()


__all__ = ["PriceAlertEvent"]
