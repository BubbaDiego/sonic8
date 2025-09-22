from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any

from backend.data.data_locker import DataLocker
from backend.core.core_constants import MOTHER_DB_PATH

router = APIRouter()


class ProfitCfg(BaseModel):
    enabled: Optional[bool] = None
    position_profit_usd: Optional[float] = None
    portfolio_profit_usd: Optional[float] = None
    notifications: Optional[Dict[str, Any]] = None


@router.get("/api/monitor-settings/profit")
def get_profit_cfg():
    dl = DataLocker.get_instance(str(MOTHER_DB_PATH))
    return (dl.system.get_var("profit_monitor") if dl.system else {}) or {}


@router.post("/api/monitor-settings/profit")
def save_profit_cfg(cfg: ProfitCfg):
    dl = DataLocker.get_instance(str(MOTHER_DB_PATH))
    current = (dl.system.get_var("profit_monitor") if dl.system else {}) or {}
    patch = {k: v for k, v in cfg.dict(exclude_unset=True).items()}
    current.update(patch)
    if dl.system:
        dl.system.set_var("profit_monitor", current)
    return {"ok": True, "config": current}


__all__ = ["router"]
