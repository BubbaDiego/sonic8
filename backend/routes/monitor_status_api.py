from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime, timezone
from backend.data.data_locker import DataLocker
from backend.deps import get_app_locker
from backend.models.monitor_status import (
    MonitorStatus,
    MonitorType,
    MonitorHealth,
    MonitorDetail,
)


router = APIRouter(prefix="/api/monitor-status", tags=["monitor_status"])


_status = MonitorStatus()

class UpdatePayload(BaseModel):
    status: MonitorHealth
    metadata: Optional[Dict] = None

def _parse_type(value: str) -> MonitorType:
    try:
        return MonitorType[value.upper()]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown monitor type") from exc

def get_sonic_next_run(dl: DataLocker):
    cursor = dl.db.get_cursor()
    cursor.execute(
        "SELECT last_run, interval_seconds FROM monitor_heartbeat WHERE monitor_name = ?",
        ("sonic_monitor",),
    )
    row = cursor.fetchone()
    if row and row[0]:
        last_run = datetime.fromisoformat(row[0]).timestamp()
        interval = int(row[1])
        next_run = last_run + interval
        return max(0, int(next_run - datetime.now(timezone.utc).timestamp()))
    return 0

def get_liquidation_snooze(dl: DataLocker):
    cfg = dl.system.get_var("liquid_monitor") or {}
    last_alert_ts = cfg.get("_last_alert_ts")
    snooze_seconds = cfg.get("snooze_seconds", 600)
    if not last_alert_ts:
        return 0
    next_alert_time = last_alert_ts + snooze_seconds
    return max(0, int(next_alert_time - datetime.now(timezone.utc).timestamp()))

@router.get("/", response_model=MonitorStatus)
def get_status(dl: DataLocker = Depends(get_app_locker)) -> MonitorStatus:
    status_summary = dl.ledger.get_monitor_status_summary()

    now = datetime.now(timezone.utc).timestamp()

    # Sonic next run calculation (safe handling)
    try:
        sonic_cursor = dl.db.get_cursor()
        sonic_cursor.execute(
            "SELECT last_run, interval_seconds FROM monitor_heartbeat WHERE monitor_name = ?",
            ("sonic_monitor",),
        )
        sonic_row = sonic_cursor.fetchone()
        if sonic_row and sonic_row[0]:
            last_run = datetime.fromisoformat(sonic_row[0]).timestamp()
            interval = int(sonic_row[1])
            sonic_next = max(0, int(last_run + interval - now))
        else:
            sonic_next = 0
    except Exception:
        sonic_next = 0

    # Liquidation snooze timer calculation (safe handling)
    try:
        liquid_snooze = get_liquidation_snooze(dl)
    except Exception:
        liquid_snooze = 0

    try:
        last_entry = dl.ledger.get_last_entry("sonic_monitor")
        if last_entry and (last_entry.get("status") == "Success"):
            sonic_last_complete = last_entry.get("timestamp")
        else:
            sonic_last_complete = None
    except Exception:
        sonic_last_complete = None

    # Return safely populated MonitorStatus
    return MonitorStatus(
        monitors=status_summary.monitors,
        sonic_next=sonic_next,
        liquid_snooze=liquid_snooze,
        sonic_last_complete=sonic_last_complete,
    )


@router.get("/{monitor_type}", response_model=MonitorDetail)
def get_monitor(monitor_type: str, dl: DataLocker = Depends(get_app_locker)) -> MonitorDetail:
    mtype = _parse_type(monitor_type)
    summary = dl.ledger.get_monitor_status_summary()
    return summary.get_monitor_status(mtype)

@router.post("/{monitor_type}", response_model=MonitorDetail)
def update_monitor(monitor_type: str, payload: UpdatePayload) -> MonitorDetail:
    mtype = _parse_type(monitor_type)
    _status.update_monitor(mtype, payload.status, payload.metadata)
    return _status.get_monitor_status(mtype)

__all__ = ["router"]
