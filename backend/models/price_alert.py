"""Price alert data models for Market Core."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

# Pydantic v1/v2 compatible fallback (same pattern as backend/models/position.py)
try:
    from pydantic import BaseModel, Field, constr, ConfigDict

    if not hasattr(BaseModel, "__fields__"):
        # Some stub pydantic builds don't behave like real models
        raise ImportError("stub")
except Exception:  # pragma: no cover - fallback when pydantic isn't available
    class BaseModel:  # type: ignore[override]
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

        def model_dump(self) -> dict:  # type: ignore
            return self.__dict__

        # pydantic v1 compatibility used in tests
        def dict(self) -> dict:  # type: ignore[override]
            return self.__dict__

    def Field(default=None, **_):  # type: ignore
        return default

    def constr(*_, **__):  # type: ignore
        return str

    ConfigDict = dict  # type: ignore


class PriceAlert(BaseModel):
    """
    Configuration + live state for a single price alert.

    This model is intentionally self-contained so we can serialize it directly
    into the ``price_alerts`` table (JSON or flattened columns) and also return
    it via API / console without extra adapters.
    """

    # ---- Identity / scope ----------------------------------------------------

    id: constr(min_length=1)
    symbol: str  # e.g. "SPX", "BTC", "ETH", "SOL"
    label: Optional[str] = None  # user-facing label for UI/XCom

    # ---- Rule definition (what the user asked for) --------------------------

    # "move_pct"  -> percent move from anchor
    # "move_abs"  -> dollar move from anchor
    # "price_target" -> fixed target price (>= or <=)
    rule_type: str = "move_pct"

    # For movement rules: "up" / "down" / "both"
    # For price targets: "above" / "below"
    direction: str = "both"

    # Original threshold specified by the user:
    #   move_pct     -> percent (e.g. 5.0 for 5%)
    #   move_abs     -> dollars (e.g. 500.0)
    #   price_target -> target price (e.g. 5200.0)
    base_threshold_value: float

    # Recurrence behaviour:
    #   "single" -> fire once then disarm until reset
    #   "reset"  -> fire, then anchor jumps to current price
    #   "ladder" -> fire on each step of size threshold in the chosen direction
    recurrence_mode: str = "single"

    # Per-alert cooldown (seconds) on top of global XCom snooze (optional)
    cooldown_seconds: int = 0

    enabled: bool = True  # if False, alert is ignored

    # ---- Anchor & recurrence state ------------------------------------------

    # Anchor at creation (or last "hard reset to original")
    original_anchor_price: Optional[float] = None
    original_anchor_ts: Optional[str] = None  # ISO 8601

    # Current anchor used for evaluation (may move in reset/ladder modes)
    current_anchor_price: Optional[float] = None
    current_anchor_ts: Optional[str] = None  # ISO 8601

    # Effective threshold currently in force (may walk in ladder mode).
    effective_threshold_value: Optional[float] = None

    # Armed vs disarmed (single-shot alerts disarm after breach)
    armed: bool = True

    # ---- Runtime telemetry ---------------------------------------------------

    last_state: Optional[str] = None  # "OK" | "WARN" | "BREACH" | "SKIP"
    last_price: Optional[float] = None
    last_move_abs: Optional[float] = None
    last_move_pct: Optional[float] = None
    last_evaluated_at: Optional[str] = None  # ISO 8601

    last_fired_at: Optional[str] = None  # ISO 8601
    fired_count: int = 0

    # ---- Misc / audit --------------------------------------------------------

    metadata: Optional[Dict[str, Any]] = None

    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    model_config = ConfigDict(from_attributes=True)


__all__ = ["PriceAlert"]
