from fastapi import APIRouter, Depends
from typing import Optional, Dict, Any
from pydantic import BaseModel

from backend.data.data_locker import DataLocker
from backend.deps import get_app_locker

router = APIRouter(prefix="/api/monitor-settings", tags=["monitor_settings"])


class LiquidCfg(BaseModel):
    enabled_sonic: Optional[bool] = None
    enabled_liquid: Optional[bool] = None
    snooze_seconds: Optional[int] = None
    blast_radius: Optional[int] = None
    thresholds: Optional[Dict[str, float]] = None
    notifications: Optional[Dict[str, Any]] = None  # {"system": bool, "voice": bool, "sms": bool, "tts": bool}


@router.get("/liquidation")
def get_liquid_cfg(dl: DataLocker = Depends(get_app_locker)):
    return dl.system.get_var("liquid_monitor") or {}


@router.post("/liquidation")
def save_liquid_cfg(cfg: LiquidCfg, dl: DataLocker = Depends(get_app_locker)):
    current = dl.system.get_var("liquid_monitor") or {}
    patch = {k: v for k, v in cfg.dict(exclude_unset=True).items()}
    if "notifications" in patch and not isinstance(patch["notifications"], dict):
        patch["notifications"] = {}
    current.update(patch)
    dl.system.set_var("liquid_monitor", current)
    return {"ok": True, "config": current}
