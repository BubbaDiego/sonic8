"""FastAPI router providing CRUD endpoints for monitor thresholds.

The previous Flask ``Blueprint`` has been replaced with :class:`APIRouter`.
"""

from fastapi import APIRouter, Depends
from backend.data.data_locker import DataLocker  # type: ignore
from backend.core.alert_core.threshold_service import ThresholdService  # type: ignore
from backend.deps import get_app_locker

router = APIRouter(prefix="/api/monitor-settings", tags=["monitor-settings"])

# ------------------------------------------------------------------ #
# Liquidation Monitor (liquid_monitor)
# ------------------------------------------------------------------ #


@router.get("/liquidation")
def get_liquidation_settings(dl: DataLocker = Depends(get_app_locker)):
    """Return the current liquidation monitor configuration."""
    return dl.system.get_var("liquid_monitor") or {}


@router.post("/liquidation")
def update_liquidation_settings(
    payload: dict, dl: DataLocker = Depends(get_app_locker)
):
    """Update threshold and snooze settings for the liquidation monitor."""
    cfg = dl.system.get_var("liquid_monitor") or {}
    cfg.update(
        {
            "threshold_percent": float(
                payload.get("threshold_percent", cfg.get("threshold_percent", 5.0))
            ),
            "snooze_seconds": int(
                payload.get("snooze_seconds", cfg.get("snooze_seconds", 300))
            ),
            "thresholds": payload.get("thresholds", cfg.get("thresholds", {})),
        }
    )
    dl.system.set_var("liquid_monitor", cfg)
    return {"success": True, "config": cfg}


# ------------------------------------------------------------------ #
# Profit Monitor thresholds (uses ThresholdService rows)
# ------------------------------------------------------------------ #


@router.get("/profit")
def get_profit_settings(dl: DataLocker = Depends(get_app_locker)):
    """Return the profit monitor threshold configuration."""
    ts = ThresholdService(dl.db)
    portfolio_th = ts.get_thresholds("TotalProfit", "Portfolio", "ABOVE")
    single_th = ts.get_thresholds("Profit", "Position", "ABOVE")
    return {
        "portfolio_low": getattr(portfolio_th, "low", None),
        "portfolio_high": getattr(portfolio_th, "high", None),
        "single_low": getattr(single_th, "low", None),
        "single_high": getattr(single_th, "high", None),
    }


@router.post("/profit")
def update_profit_settings(payload: dict, dl: DataLocker = Depends(get_app_locker)):
    """Update profit monitor thresholds."""
    ts = ThresholdService(dl.db)
    ts.set_threshold(
        "TotalProfit",
        "Portfolio",
        payload.get("portfolio_low"),
        payload.get("portfolio_high"),
    )
    ts.set_threshold(
        "Profit", "Position", payload.get("single_low"), payload.get("single_high")
    )
    return {"success": True}


__all__ = ["router"]
