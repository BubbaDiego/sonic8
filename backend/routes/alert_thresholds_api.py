from __future__ import annotations

from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException

from backend.data.data_locker import DataLocker
from backend.core.alert_core.threshold_service import ThresholdService
from backend.models.alert_thresholds import AlertThreshold

router = APIRouter(prefix="/alert_thresholds", tags=["alert_thresholds"])


def _service() -> ThresholdService:
    dl = DataLocker.get_instance()
    return ThresholdService(dl.db)


@router.get("/", response_model=list[AlertThreshold])
def list_thresholds(service: ThresholdService = Depends(_service)):
    return service.list_all_thresholds()


@router.get("/{threshold_id}", response_model=AlertThreshold | None)
def get_threshold(threshold_id: str, service: ThresholdService = Depends(_service)):
    return service.repo.get_by_id(threshold_id)


@router.post("/", response_model=AlertThreshold, status_code=201)
def create_threshold(threshold: AlertThreshold, service: ThresholdService = Depends(_service)):
    if not threshold.id:
        threshold.id = str(uuid4())
    if not service.create_threshold(threshold):
        raise HTTPException(500, "Insert failed")
    return threshold


@router.put("/{threshold_id}")
def update_threshold(threshold_id: str, updates: dict, service: ThresholdService = Depends(_service)):
    ok = service.update_threshold(threshold_id, updates)
    if not ok:
        raise HTTPException(404, "Update failed")
    return {"status": "updated"}


@router.delete("/{threshold_id}")
def delete_threshold(threshold_id: str, service: ThresholdService = Depends(_service)):
    service.delete_threshold(threshold_id)
    return {"status": "deleted"}


# --- Legacy alert endpoints for backward compatibility ---
alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])


def _dl() -> DataLocker:
    return DataLocker.get_instance()


@alerts_router.post("/refresh")
def refresh_alerts(dl: DataLocker = Depends(_dl)):
    # Placeholder refresh logic; success even if no action.
    try:
        dl.alerts.get_all_alerts()
        return {"success": True}
    except Exception:
        raise HTTPException(500, "Refresh failed")


@alerts_router.post("/create_all")
def create_all_alerts(dl: DataLocker = Depends(_dl)):
    import json
    from backend.core.constants import CONFIG_DIR

    path = CONFIG_DIR / "sample_alerts.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            alerts = json.load(f)
        for a in alerts:
            dl.alerts.create_alert(a)
        return {"success": True}
    except Exception as exc:
        raise HTTPException(500, str(exc))


@alerts_router.post("/delete_all")
def delete_all_alerts(dl: DataLocker = Depends(_dl)):
    dl.alerts.delete_all_alerts()
    return {"success": True}


@alerts_router.get("/monitor")
def monitor_alerts(dl: DataLocker = Depends(_dl)):
    alerts = dl.alerts.get_all_alerts()
    return {"alerts": alerts}


# expose combined routers
__all__ = ["router", "alerts_router"]
