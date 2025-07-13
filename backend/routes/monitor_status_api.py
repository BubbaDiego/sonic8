from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict
from backend.data.data_locker import DataLocker
from backend.deps import get_app_locker

from backend.models.monitor_status import (
    MonitorStatus,
    MonitorType,
    MonitorHealth,
    MonitorDetail,
)

router = APIRouter(prefix="/monitor_status", tags=["monitor_status"])

_status = MonitorStatus()


class UpdatePayload(BaseModel):
    status: MonitorHealth
    metadata: Optional[Dict] = None


def _parse_type(value: str) -> MonitorType:
    try:
        return MonitorType[value.upper()]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Unknown monitor type") from exc


@router.get("/", response_model=MonitorStatus)
def get_status(dl: DataLocker = Depends(get_app_locker)) -> MonitorStatus:
    """Return current monitor status snapshot."""
    return dl.ledger.get_monitor_status_summary()


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
