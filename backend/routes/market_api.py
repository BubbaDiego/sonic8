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
    return {d["asset"]: d["windows"] for d in payload.get("details", [])}

__all__ = ["router"]
