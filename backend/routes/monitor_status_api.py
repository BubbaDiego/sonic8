from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from data.data_locker import DataLocker

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
def get_status() -> MonitorStatus:
    """Return current monitor status snapshot."""
    dl = DataLocker.get_instance()
    return dl.ledger.get_monitor_status_summary()


@router.get("/{monitor_type}", response_model=MonitorDetail)
def get_monitor(monitor_type: str) -> MonitorDetail:
    mtype = _parse_type(monitor_type)
    summary = DataLocker.get_instance().ledger.get_monitor_status_summary()
    return summary.get_monitor_status(mtype)


@router.post("/{monitor_type}", response_model=MonitorDetail)
def update_monitor(monitor_type: str, payload: UpdatePayload) -> MonitorDetail:
    mtype = _parse_type(monitor_type)
    _status.update_monitor(mtype, payload.status, payload.metadata)
    return _status.get_monitor_status(mtype)


__all__ = ["router"]
