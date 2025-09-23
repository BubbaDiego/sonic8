from fastapi import APIRouter, Depends
from backend.data.data_locker import DataLocker
from backend.deps import get_app_locker
import json
from typing import Any, Dict, Optional, Mapping

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/latest")
def market_latest(dl: DataLocker = Depends(get_app_locker)) -> Dict[str, Dict[str, Any]]:
    row = dl.ledger.get_latest_entry("market_monitor", status="Success")
    if not row:
        return {}

    metadata = row
    if isinstance(row, Mapping):
        metadata = row.get("metadata")
    else:
        metadata = row[0]

    if metadata is None:
        return {}

    payload = json.loads(metadata)
    details = payload.get("details", []) or []

    def _f(value: Any) -> Optional[float]:
        try:
            return float(value)
        except Exception:
            return None

    def _b(value: Any) -> Optional[bool]:
        if value is None:
            return None
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "y"}:
                return True
            if lowered in {"false", "0", "no", "n"}:
                return False
        return bool(value)

    latest: Dict[str, Dict[str, Any]] = {}
    for detail in details:
        asset = detail.get("asset")
        if not asset:
            continue

        if "windows" in detail and isinstance(detail["windows"], dict):
            latest[asset] = detail["windows"]
            continue

        anchor = detail.get("anchor")
        if isinstance(anchor, dict):
            anchor = anchor.get("value")

        price = detail.get("current")
        if price is None:
            price = detail.get("price")
        move = detail.get("move")
        thr = detail.get("threshold")
        if thr is None:
            thr = detail.get("delta")
        triggered = detail.get("triggered")
        if triggered is None:
            triggered = detail.get("trigger")
        dir_ok = detail.get("dir_ok")
        direction = (detail.get("direction") or "both").lower()

        if move is None and price is not None and anchor is not None:
            pf, af = _f(price), _f(anchor)
            if pf is not None and af is not None:
                move = pf - af

        latest[asset] = {
            "anchor": _f(anchor) if anchor is not None else None,
            "current": _f(price) if price is not None else None,
            "move": _f(move) if move is not None else None,
            "threshold": _f(thr) if thr is not None else None,
            "direction": direction,
            "dir_ok": _b(dir_ok),
            "triggered": _b(triggered),
        }

    return latest

__all__ = ["router"]
