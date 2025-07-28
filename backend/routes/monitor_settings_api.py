"""FastAPI router providing CRUD endpoints for monitor thresholds.

v2 – Adds nested ``notifications`` dict (system / voice / sms / tts) to liquidation monitor schema.
Back‑compat: still accepts flat ``threshold_btc`` etc. and old ``windows_alert`` / ``voice_alert`` flags.
"""

from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from backend.data.data_locker import DataLocker  # type: ignore
from backend.core.alert_core.threshold_service import ThresholdService  # type: ignore
from backend.core.monitor_core.sonic_monitor import DEFAULT_INTERVAL, MONITOR_NAME
from backend.core.monitor_core import market_monitor
from backend.deps import get_app_locker

router = APIRouter(prefix="/api/monitor-settings", tags=["monitor-settings"])

# ------------------------------------------------------------------ #
# Market Monitor settings
# ------------------------------------------------------------------ #


@router.get("/market")
def get_market_settings(dl: DataLocker = Depends(get_app_locker)):
    """Return current MarketMonitor configuration with defaults."""

    monitor = market_monitor.MarketMonitor()
    monitor.dl = dl

    cfg = dl.system.get_var("market_monitor")
    if cfg is None:
        return monitor._cfg()

    defaults = monitor._cfg()
    defaults.update(cfg)
    return defaults


@router.post("/market")
def update_market_settings(payload: dict, dl: DataLocker = Depends(get_app_locker)):
    dl.system.set_var("market_monitor", payload)
    return {"success": True}


# ------------------------------------------------------------------ #
# Sonic loop interval
# ------------------------------------------------------------------ #


@router.get("/sonic")
def get_sonic_settings(dl: DataLocker = Depends(get_app_locker)):
    """Return current Sonic monitor loop interval."""

    cursor = dl.db.get_cursor()
    if cursor is None:
        return {"interval_seconds": DEFAULT_INTERVAL}
    cursor.execute(
        "SELECT interval_seconds FROM monitor_heartbeat WHERE monitor_name = ?",
        (MONITOR_NAME,),
    )
    row = cursor.fetchone()
    if row and row[0] is not None:
        return {"interval_seconds": int(row[0])}
    return {"interval_seconds": DEFAULT_INTERVAL}


@router.post("/sonic")
def update_sonic_settings(payload: dict, dl: DataLocker = Depends(get_app_locker)):
    """Update Sonic monitor loop interval."""

    interval = int(payload.get("interval_seconds", DEFAULT_INTERVAL))

    cursor = dl.db.get_cursor()
    if cursor is None:
        return {"success": False}
    cursor.execute(
        "SELECT last_run FROM monitor_heartbeat WHERE monitor_name = ?",
        (MONITOR_NAME,),
    )
    row = cursor.fetchone()
    last_run = row[0] if row else datetime.now(timezone.utc).isoformat()
    cursor.execute(
        """
        INSERT INTO monitor_heartbeat (monitor_name, last_run, interval_seconds)
        VALUES (?, ?, ?)
        ON CONFLICT(monitor_name) DO UPDATE SET interval_seconds = excluded.interval_seconds
        """,
        (MONITOR_NAME, last_run, interval),
    )
    dl.db.commit()
    return {"success": True}


# ------------------------------------------------------------------ #
# Liquidation Monitor (liquid_monitor)
# ------------------------------------------------------------------ #


def _merge_liq_config(cfg: dict, payload: dict) -> dict:
    """Return merged config respecting new + legacy keys."""
    cfg = cfg.copy()

    def to_bool(value):
        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes", "on")
        return bool(value)

    # --- Global fields ------------------------------------------------
    cfg["threshold_percent"] = float(
        payload.get("threshold_percent", cfg.get("threshold_percent", 5.0))
    )
    cfg["snooze_seconds"] = int(
        payload.get("snooze_seconds", cfg.get("snooze_seconds", 300))
    )
    cfg["enabled"] = to_bool(payload.get("enabled", cfg.get("enabled", True)))

    # Enabled flag ----------------------------------------------------
    cfg["enabled"] = to_bool(payload.get("enabled", cfg.get("enabled", True)))

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
    elif isinstance(thresholds, dict):
        # Cast each provided value to float when merging
        casted = {}
        for sym, value in thresholds.items():
            try:
                casted[sym] = float(value)
            except Exception:
                # Skip values that cannot be converted
                pass
        thresholds = casted
    else:
        thresholds = {}

    cfg["thresholds"] = thresholds or cfg.get("thresholds", {})

    # --- Notifications ----------------------------------------------
    notifications = payload.get("notifications")
    if notifications is None or not isinstance(notifications, dict):
        # Map any flat keys so that UI relying on old names still works
        notifications = {
            "system": to_bool(
                payload.get("windows_alert", cfg.get("windows_alert", True))
            ),
            "voice": to_bool(payload.get("voice_alert", cfg.get("voice_alert", True))),
            "sms": to_bool(payload.get("sms_alert", cfg.get("sms_alert", False))),
            "tts": to_bool(payload.get("tts_alert", cfg.get("tts_alert", True))),
        }
    # Ensure booleans
    notifications = {
        "system": to_bool(notifications.get("system")),
        "voice": to_bool(notifications.get("voice")),
        "sms": to_bool(notifications.get("sms")),
        "tts": to_bool(notifications.get("tts")),
    }
    cfg["notifications"] = notifications

    # Preserve legacy flags for the monitor until fully migrated
    cfg["windows_alert"] = notifications["system"]
    cfg["voice_alert"] = notifications["voice"]
    cfg["sms_alert"] = notifications["sms"]
    cfg["tts_alert"] = notifications["tts"]

    return cfg


@router.get("/liquidation")
def get_liquidation_settings(dl: DataLocker = Depends(get_app_locker)):
    """Return the current liquidation monitor configuration."""
    cfg = dl.system.get_var("liquid_monitor") or {}
    # Ensure defaults so that frontend checkboxes have values
    cfg.setdefault("thresholds", {})
    cfg.setdefault(
        "notifications",
        {"system": True, "voice": True, "sms": False, "tts": True},
    )
    cfg.setdefault("enabled", True)
    return cfg


@router.post("/liquidation")
def update_liquidation_settings(
    payload: dict, dl: DataLocker = Depends(get_app_locker)
):
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
    cfg = dl.system.get_var("profit_monitor") or {}
    notifications = cfg.get("notifications") or {
        "system": True,
        "voice": True,
        "sms": False,
        "tts": True,
    }
    enabled = cfg.get("enabled", True)
    return {
        "portfolio_low": getattr(portfolio_th, "low", None),
        "portfolio_high": getattr(portfolio_th, "high", None),
        "single_low": getattr(single_th, "low", None),
        "single_high": getattr(single_th, "high", None),
        "notifications": notifications,

        "enabled": cfg.get("enabled", True),

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

    cfg = dl.system.get_var("profit_monitor") or {}

    changed = False

    def to_bool(v):
        if isinstance(v, str):
            return v.lower() in ("1", "true", "yes", "on")
        return bool(v)

    if "enabled" in payload:
        cfg["enabled"] = to_bool(payload.get("enabled"))
        changed = True

    notifs = payload.get("notifications")
    if isinstance(notifs, dict):
        cfg["notifications"] = {
            "system": to_bool(notifs.get("system")),
            "voice": to_bool(notifs.get("voice")),
            "sms": to_bool(notifs.get("sms")),
            "tts": to_bool(notifs.get("tts")),
        }

        changed = True

    if changed:
        dl.system.set_var("profit_monitor", cfg)

    return {"success": True, "config": cfg}


__all__ = ["router"]
