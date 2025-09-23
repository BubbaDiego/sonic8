from fastapi import APIRouter, Depends
from backend.data.data_locker import DataLocker
from backend.deps import get_app_locker
import json

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/latest")
def market_latest(dl: DataLocker = Depends(get_app_locker)):
    cursor = dl.db.get_cursor()
    cursor.execute(
        "SELECT metadata FROM monitor_ledger "
        "WHERE monitor_name = 'market_monitor' "
        "AND status = 'Success' "
        "ORDER BY created_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    if not row:
        return {}

    payload = json.loads(row[0]) if isinstance(row[0], (str, bytes)) else json.loads(row["metadata"])
    details = payload.get("details", []) or []

    # Support both legacy "windows" shape and the new market-movement detail shape.
    latest = {}
    for detail in details:
        asset = detail.get("asset")
        if not asset:
            continue

        if "windows" in detail:  # Legacy shape: {"asset": "...", "windows": {...}}
            latest[asset] = detail["windows"]
            continue

        anchor = detail.get("anchor")
        if isinstance(anchor, dict):
            anchor = anchor.get("value")

        latest[asset] = {
            "anchor": anchor,
            "current": detail.get("current") or detail.get("price"),
            "delta": detail.get("delta"),
            "threshold": detail.get("threshold"),
            "direction": detail.get("direction"),
            "dir_ok": detail.get("dir_ok"),
            "triggered": detail.get("triggered") or detail.get("trigger"),
        }

    return latest

__all__ = ["router"]
