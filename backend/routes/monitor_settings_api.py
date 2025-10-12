"""FastAPI router providing CRUD endpoints for monitor thresholds.

v2 – Adds nested ``notifications`` dict (system / voice / sms / tts) to liquidation monitor schema.
Back‑compat: still accepts flat ``threshold_btc`` etc. and old ``windows_alert`` / ``voice_alert`` flags.
"""

from fastapi import APIRouter, Depends, status
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from backend.data.data_locker import DataLocker  # type: ignore
from backend.core.alert_core.threshold_service import ThresholdService  # type: ignore
from backend.core.core_constants import MOTHER_DB_PATH
from backend.core.monitor_core.sonic_monitor import DEFAULT_INTERVAL, MONITOR_NAME
from backend.core.monitor_core import market_monitor
from backend.deps import get_app_locker

router = APIRouter(prefix="/api/monitor-settings", tags=["monitor_settings"])


def _read_interval(dl: DataLocker) -> int:
    """Return Sonic loop interval from the heartbeat table, defaulting when absent."""

    cursor = dl.db.get_cursor()
    if cursor is None:
        return int(DEFAULT_INTERVAL)

    cursor.execute(
        "SELECT interval_seconds FROM monitor_heartbeat WHERE monitor_name = ?",
        (MONITOR_NAME,),
    )
    row = cursor.fetchone()
    return int(row[0]) if row and row[0] is not None else int(DEFAULT_INTERVAL)

# ------------------------------------------------------------------ #
# Market Movement Monitor settings
# ------------------------------------------------------------------ #


@router.post("/market/reset-anchors")
def reset_market_anchors():
    dl = DataLocker.get_instance(str(MOTHER_DB_PATH))
    cfg = (dl.system.get_var("market_monitor") if dl.system else {}) or {}

    mon = market_monitor.MarketMonitor(dl)
    # Ensure defaults such as thresholds/anchors exist
    cfg = mon._cfg()

    thresholds = cfg.get("thresholds") or {}
    assets = list(thresholds.keys()) or list(getattr(mon, "ASSETS", [])) or ["BTC", "ETH", "SOL"]

    anchors = {}
    now = datetime.now(timezone.utc).isoformat()
    for asset in assets:
        price_info = dl.get_latest_price(asset) or {}
        price = price_info.get("current_price") if isinstance(price_info, dict) else None
        if price is None:
            continue

        anchors[asset] = {"value": float(price), "time": now}
        cfg.setdefault("anchors", {})[asset] = anchors[asset]
        cfg.setdefault("armed", {})[asset] = True

    if dl.system:
        dl.system.set_var(mon.name, cfg)

    return {"anchors": anchors, "armed": cfg.get("armed", {})}


# ------------------------------------------------------------------ #
# Sonic loop interval
# ------------------------------------------------------------------ #


@router.get("/sonic")
def get_sonic_settings(dl: DataLocker = Depends(get_app_locker)):
    """Return current Sonic monitor settings."""

    interval = _read_interval(dl)

    cfg = dl.system.get_var("sonic_monitor") or {}
    return {
        "interval_seconds": interval,
        "enabled_sonic": cfg.get("enabled_sonic", True),
        "enabled_liquid": cfg.get("enabled_liquid", True),
        "enabled_profit": cfg.get("enabled_profit", True),
        "enabled_market": cfg.get("enabled_market", True),
    }


@router.post("/sonic")
def update_sonic_settings(payload: dict, dl: DataLocker = Depends(get_app_locker)):
    """Update Sonic monitor settings."""

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

    cfg = dl.system.get_var("sonic_monitor") or {}

    def to_bool(value):
        if isinstance(value, str):
            return value.lower() in ("1", "true", "yes", "on")
        return bool(value)

    for key in ["enabled_sonic", "enabled_liquid", "enabled_profit", "enabled_market"]:
        if key in payload:
            cfg[key] = to_bool(payload.get(key))
        else:
            cfg.setdefault(key, True)

    dl.system.set_var("sonic_monitor", cfg)

    return {"success": True, "config": {"interval_seconds": interval, **cfg}}


class ProvenanceResponse(BaseModel):
    interval: Dict[str, Any]
    thresholds: Dict[str, Any]
    thresholds_label: str


# ----------------------- Provenance (new) -----------------------
# Return where the loop actually sourced its thresholds and the DB table for the loop interval.


@router.get("/provenance", response_model=ProvenanceResponse)
def get_provenance(dl: DataLocker = Depends(get_app_locker)):
    """
    Report Sonic loop provenance for diagnostics.

    Returns:
        interval: {'seconds': int, 'source': 'db', 'table': 'monitor_heartbeat'}
        thresholds: nested dict of values observed by the loop
        thresholds_label: description of source(s) such as
                          'DL.system_vars (...path)', 'global_config (...path)',
                          'env (...file)', or 'mixed: A + B'
    """

    # Interval always comes from the monitor_heartbeat table unless unavailable
    try:
        seconds = _read_interval(dl)  # uses monitor_heartbeat under the hood
    except Exception:
        seconds = int(DEFAULT_INTERVAL)

    # Thresholds + provenance label come from the Sonic loop's resolver helper
    try:
        from backend.core.monitor_core.sonic_monitor import (  # type: ignore
            _read_monitor_threshold_sources,
        )

        thresholds, label = _read_monitor_threshold_sources(dl)
    except Exception:
        thresholds, label = {}, ""

    return {
        "interval": {
            "seconds": int(seconds),
            "source": "db",
            "table": "monitor_heartbeat",
        },
        "thresholds": thresholds or {},
        "thresholds_label": label or "",
    }


# ------------------------------------------------------------------ #
# Liquidation & Market Monitor system_var helpers
# ------------------------------------------------------------------ #


def _dl_get_system_var(dl: DataLocker, key: str, default: Any = None) -> Any:
    """Fetch a system-level value from any available accessor on DataLocker."""

    system_mgr = getattr(dl, "system", None)
    if system_mgr is not None:
        try:
            value = system_mgr.get_var(key)
        except Exception:
            value = None
        if value is not None:
            return value

    for name in ("get_system_var", "get_sysvar", "get_var", "system_var_get"):
        func = getattr(dl, name, None)
        if callable(func):
            try:
                return func(key)
            except TypeError:
                try:
                    return func(key, default)
                except Exception:
                    continue
            except Exception:
                continue

    system_vars = getattr(dl, "system_vars", None)
    if isinstance(system_vars, dict):
        return system_vars.get(key, default)

    return default


def _dl_set_system_var(dl: DataLocker, key: str, value: Any) -> None:
    """Persist a system-level value via the best available accessor."""

    system_mgr = getattr(dl, "system", None)
    if system_mgr is not None:
        try:
            system_mgr.set_var(key, value)
            return
        except Exception:
            pass

    for name in ("set_system_var", "set_sysvar", "set_var", "system_var_set"):
        func = getattr(dl, name, None)
        if callable(func):
            try:
                func(key, value)
                return
            except Exception:
                continue

    system_vars = getattr(dl, "system_vars", None)
    if isinstance(system_vars, dict):
        system_vars[key] = value


class LiquidationSettings(BaseModel):
    thresholds: Dict[str, Any] = Field(default_factory=dict)
    blast_radius: Dict[str, Any] = Field(default_factory=dict)
    notifications: Dict[str, bool] = Field(default_factory=dict)
    enabled_liquid: Optional[bool] = None


def _num(value: Any, default: float | None = 0.0) -> float | None:
    if value is None or value == "":
        return default
    try:
        return float(str(value).replace(",", ""))
    except Exception:
        return default


def _normalize_liq(payload: LiquidationSettings) -> Dict[str, Any]:
    thresholds = payload.thresholds or {}
    blast_radius = payload.blast_radius or {}

    normalized_thresholds = {k.upper(): _num(v, 0.0) for k, v in thresholds.items()}
    normalized_blast = {k.upper(): _num(v, 0.0) for k, v in blast_radius.items()}

    notifications = {"system": True, "voice": True, "sms": False, "tts": True}
    notifications.update(payload.notifications or {})

    cfg: Dict[str, Any] = {
        "thresholds": normalized_thresholds,
        "blast_radius": normalized_blast,
        "notifications": notifications,
    }

    if payload.enabled_liquid is not None:
        cfg["enabled_liquid"] = bool(payload.enabled_liquid)

    return cfg


@router.get("/liquidation", response_model=LiquidationSettings)
def get_liquidation_settings(dl: DataLocker = Depends(get_app_locker)):
    data = _dl_get_system_var(dl, "liquid_monitor", {}) or {}
    return LiquidationSettings(
        thresholds=data.get("thresholds", {}),
        blast_radius=data.get("blast_radius", {}),
        notifications=data.get("notifications", {}),
        enabled_liquid=data.get("enabled_liquid"),
    )


@router.post("/liquidation", status_code=status.HTTP_204_NO_CONTENT)
def post_liquidation_settings(
    payload: LiquidationSettings, dl: DataLocker = Depends(get_app_locker)
):
    shaped = _normalize_liq(payload)
    _dl_set_system_var(dl, "liquid_monitor", shaped)


class MarketSettings(BaseModel):
    thresholds: Dict[str, Any] = Field(default_factory=dict)
    rearm_mode: Optional[str] = None
    notifications: Dict[str, bool] = Field(default_factory=dict)
    enabled_market: Optional[bool] = None


def _normalize_market(payload: MarketSettings) -> Dict[str, Any]:
    normalized: Dict[str, Dict[str, Any]] = {}
    for asset, value in (payload.thresholds or {}).items():
        if isinstance(value, dict):
            delta = _num(value.get("delta"), 0.0)
            direction = str(value.get("direction", "both")).lower()
        else:
            delta = _num(value, 0.0)
            direction = "both"
        normalized[asset.upper()] = {"delta": delta, "direction": direction}

    notifications = {"system": True, "voice": True, "sms": False, "tts": True}
    notifications.update(payload.notifications or {})

    cfg: Dict[str, Any] = {
        "thresholds": normalized,
        "notifications": notifications,
    }

    if payload.rearm_mode:
        cfg["rearm_mode"] = payload.rearm_mode.lower()
    if payload.enabled_market is not None:
        cfg["enabled_market"] = bool(payload.enabled_market)

    return cfg


@router.get("/market", response_model=MarketSettings)
def get_market_settings(dl: DataLocker = Depends(get_app_locker)):
    data = _dl_get_system_var(dl, "market_monitor", {}) or {}
    return MarketSettings(
        thresholds=data.get("thresholds", {}),
        rearm_mode=data.get("rearm_mode"),
        notifications=data.get("notifications", {}),
        enabled_market=data.get("enabled_market"),
    )


@router.post("/market", status_code=status.HTTP_204_NO_CONTENT)
def post_market_settings(payload: MarketSettings, dl: DataLocker = Depends(get_app_locker)):
    shaped = _normalize_market(payload)
    _dl_set_system_var(dl, "market_monitor", shaped)


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
