"""FastAPI router providing CRUD endpoints for monitor thresholds.

v2 – Adds nested ``notifications`` dict (system / voice / sms) to liquidation monitor schema.
Back‑compat: still accepts flat ``threshold_btc`` etc. and old ``windows_alert`` / ``voice_alert`` flags.
"""

from fastapi import APIRouter, Depends
from backend.data.data_locker import DataLocker  # type: ignore
from backend.core.alert_core.threshold_service import ThresholdService  # type: ignore
from backend.deps import get_app_locker

router = APIRouter(prefix="/api/monitor-settings", tags=["monitor-settings"])

# ------------------------------------------------------------------ #
# Liquidation Monitor (liquid_monitor)
# ------------------------------------------------------------------ #


def _merge_liq_config(cfg: dict, payload: dict) -> dict:
    """Return merged config respecting new + legacy keys."""
    cfg = cfg.copy()

    # --- Global fields ------------------------------------------------
    cfg["threshold_percent"] = float(
        payload.get("threshold_percent", cfg.get("threshold_percent", 5.0))
    )
    cfg["snooze_seconds"] = int(
        payload.get("snooze_seconds", cfg.get("snooze_seconds", 300))
    )

    # --- Thresholds dict ---------------------------------------------
    thresholds = payload.get("thresholds")
    if thresholds is None:
        # Fallback to legacy ``threshold_btc`` style keys
        thresholds = {}
        for sym in ("btc", "eth", "sol"):
            if (k := f"threshold_{sym}") in payload:
                try:
                    thresholds[sym.upper()] = float(payload[k])
                except Exception:
                    pass
    else:
        # Cast each provided value to float when merging
        casted = {}
        for sym, value in thresholds.items():
            try:
                casted[sym] = float(value)
            except Exception:
                # Skip values that cannot be converted
                pass
        thresholds = casted

    cfg["thresholds"] = thresholds or cfg.get("thresholds", {})

    # --- Notifications ----------------------------------------------
    notifications = payload.get("notifications")
    if notifications is None:
        # Map any flat keys so that UI relying on old names still works
        notifications = {
            "system": bool(payload.get("windows_alert", cfg.get("windows_alert", True))),
            "voice": bool(payload.get("voice_alert", cfg.get("voice_alert", True))),
            "sms": bool(payload.get("sms_alert", cfg.get("sms_alert", False))),
        }
    # Ensure booleans
    notifications = {
        "system": bool(notifications.get("system")),
        "voice": bool(notifications.get("voice")),
        "sms": bool(notifications.get("sms")),
    }
    cfg["notifications"] = notifications

    # Preserve legacy flags for the monitor until fully migrated
    cfg["windows_alert"] = notifications["system"]
    cfg["voice_alert"] = notifications["voice"]
    cfg["sms_alert"] = notifications["sms"]

    return cfg


@router.get("/liquidation")
def get_liquidation_settings(dl: DataLocker = Depends(get_app_locker)):
    """Return the current liquidation monitor configuration."""
    cfg = dl.system.get_var("liquid_monitor") or {}
    # Ensure defaults so that frontend checkboxes have values
    cfg.setdefault("thresholds", {})
    cfg.setdefault("notifications", {"system": True, "voice": True, "sms": False})
    return cfg


@router.post("/liquidation")
def update_liquidation_settings(payload: dict, dl: DataLocker = Depends(get_app_locker)):
    """Update liquidation monitor settings.

    Accepts both new nested structure and legacy flat keys.
    """
    existing = dl.system.get_var("liquid_monitor") or {}
    cfg = _merge_liq_config(existing, payload)
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
