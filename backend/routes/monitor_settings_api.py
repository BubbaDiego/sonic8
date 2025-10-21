"""FastAPI router providing CRUD endpoints for monitor thresholds.

v2 – Adds nested ``notifications`` dict (system / voice / sms / tts) to liquidation monitor schema.
Back‑compat: still accepts flat ``threshold_btc`` etc. and old ``windows_alert`` / ``voice_alert`` flags.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field, ValidationError

from backend.data.data_locker import DataLocker  # type: ignore
from backend.config.config_loader import load_monitor_config, save_monitor_config
from backend.core.alert_core.threshold_service import ThresholdService  # type: ignore
from backend.core.config.json_config import (
    get_path_str,
    load_config as load_json_cfg,
    save_config_patch,
)
from backend.core.core_constants import MOTHER_DB_PATH
from backend.core.monitor_core.sonic_monitor import DEFAULT_INTERVAL, MONITOR_NAME
from backend.core.monitor_core import market_monitor
from backend.deps import get_app_locker
from backend.core.config_core import sonic_config_bridge as C


log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/monitor-settings", tags=["monitor_settings"])


def _read_interval(dl: DataLocker) -> tuple[int, str]:
    """Return the Sonic loop interval and the backing source."""

    try:
        cfg = load_json_cfg()
        seconds = int(
            cfg.get("system_config", {})
            .get("sonic_monitor_loop_time", 0)
            or 0
        )
        if seconds > 0:
            return seconds, "json"
    except Exception:
        pass

    cursor = dl.db.get_cursor()
    if cursor is None:
        return int(DEFAULT_INTERVAL), "default"

    cursor.execute(
        "SELECT interval_seconds FROM monitor_heartbeat WHERE monitor_name = ?",
        (MONITOR_NAME,),
    )
    row = cursor.fetchone()
    if row and row[0] is not None:
        try:
            return int(row[0]), "db"
        except Exception:
            pass
    return int(DEFAULT_INTERVAL), "default"


def _monitor_json_state() -> Dict[str, Any]:
    data = load_monitor_config()
    return dict(data) if isinstance(data, dict) else {}


def _persist_monitor_json(
    *,
    loop_seconds: Optional[int] = None,
    enabled: Optional[Dict[str, Any]] = None,
    xcom_live: Optional[bool] = None,
    price_assets: Optional[Any] = None,
    liquid: Optional[Dict[str, Any]] = None,
    profit: Optional[Dict[str, Any]] = None,
    twilio: Optional[Dict[str, Any]] = None,
) -> None:
    cfg = _monitor_json_state()

    monitor_section = cfg.setdefault("monitor", {})
    if loop_seconds is not None:
        try:
            monitor_section["loop_seconds"] = int(loop_seconds)
        except Exception:
            pass
    if enabled:
        enabled_section = monitor_section.setdefault("enabled", {})
        for key, value in enabled.items():
            enabled_section[key] = bool(value)
    if xcom_live is not None:
        monitor_section["xcom_live"] = bool(xcom_live)

    if price_assets is not None:
        assets: list[str] = []
        for asset in price_assets:
            if asset is None:
                continue
            text = str(asset).strip()
            if text:
                assets.append(text.upper())
        if assets:
            cfg.setdefault("price", {})["assets"] = assets

    if liquid:
        liq_section = cfg.setdefault("liquid", {})
        thresholds = liquid.get("thresholds") if isinstance(liquid, dict) else None
        blast = liquid.get("blast") if isinstance(liquid, dict) else None
        if isinstance(thresholds, dict):
            shaped = {}
            for key, value in thresholds.items():
                try:
                    shaped[str(key).upper()] = float(value)
                except Exception:
                    continue
            if shaped:
                liq_section["thresholds"] = shaped
        if isinstance(blast, dict):
            shaped_blast = {}
            for key, value in blast.items():
                try:
                    shaped_blast[str(key).upper()] = float(value)
                except Exception:
                    continue
            if shaped_blast:
                liq_section["blast"] = shaped_blast

    if profit:
        prof_section = cfg.setdefault("profit", {})
        if "position_usd" in profit and profit["position_usd"] is not None:
            try:
                prof_section["position_usd"] = int(float(profit["position_usd"]))
            except Exception:
                pass
        if "portfolio_usd" in profit and profit["portfolio_usd"] is not None:
            try:
                prof_section["portfolio_usd"] = int(float(profit["portfolio_usd"]))
            except Exception:
                pass

    if twilio:
        twilio_section = cfg.setdefault("twilio", {})
        for key in ("sid", "auth", "from", "to", "flow"):
            value = twilio.get(key) if isinstance(twilio, dict) else None
            if value is not None:
                twilio_section[key] = value

    save_monitor_config(cfg)

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

    interval, _ = _read_interval(dl)

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

    xcom_live_val = payload.get("xcom_live")
    if xcom_live_val is not None:
        xcom_live = to_bool(xcom_live_val)
        os.environ["SONIC_XCOM_LIVE"] = "1" if xcom_live else "0"
    else:
        xcom_live = C.get_xcom_live()

    try:
        save_config_patch(
            {"system_config": {"sonic_monitor_loop_time": int(interval)}}
        )
    except Exception:
        log.debug("Failed to persist sonic loop interval to JSON", exc_info=True)

    enabled_snapshot = {
        "sonic": cfg.get("enabled_sonic", True),
        "liquid": cfg.get("enabled_liquid", True),
        "profit": cfg.get("enabled_profit", True),
        "market": cfg.get("enabled_market", True),
        "price": cfg.get("enabled_market", True),
    }

    _persist_monitor_json(
        loop_seconds=interval,
        enabled=enabled_snapshot,
        xcom_live=xcom_live,
    )

    return {"success": True, "config": {"interval_seconds": interval, **cfg}}


class ProvenanceResponse(BaseModel):
    interval: Dict[str, Any]
    thresholds: Dict[str, Any]
    thresholds_label: str
    json_path: Optional[str] = None
    json_used: Optional[bool] = None


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

    # Interval prefers JSON override then falls back to the monitor_heartbeat table.
    try:
        seconds, interval_source = _read_interval(dl)
    except Exception:
        seconds, interval_source = int(DEFAULT_INTERVAL), "default"

    # Thresholds + provenance label come from the Sonic loop's resolver helper
    try:
        from backend.core.monitor_core.sonic_monitor import (  # type: ignore
            _read_monitor_threshold_sources,
        )

        thresholds, label = _read_monitor_threshold_sources(dl)
    except Exception:
        thresholds, label = {}, ""

    json_path = get_path_str()
    json_used = interval_source == "json" or label == "JSON"

    return {
        "interval": {
            "seconds": int(seconds),
            "source": interval_source,
            "table": "monitor_heartbeat",
        },
        "thresholds": thresholds or {},
        "thresholds_label": label or "",
        "json_path": json_path,
        "json_used": json_used,
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


def _json_section(key: str) -> Dict[str, Any]:
    try:
        cfg = load_json_cfg()
    except Exception:
        return {}

    section = cfg.get(key)
    return dict(section) if isinstance(section, dict) else {}


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

    cfg["windows_alert"] = bool(notifications.get("system"))
    cfg["voice_alert"] = bool(notifications.get("voice"))
    cfg["sms_alert"] = bool(notifications.get("sms"))
    cfg["tts_alert"] = bool(notifications.get("tts"))

    if payload.enabled_liquid is not None:
        enabled_value = bool(payload.enabled_liquid)
        cfg["enabled_liquid"] = enabled_value
        cfg["enabled"] = enabled_value

    return cfg


@router.get("/liquidation", response_model=LiquidationSettings)
def get_liquidation_settings(dl: DataLocker = Depends(get_app_locker)):
    data = _dl_get_system_var(dl, "liquid_monitor", {}) or {}
    json_cfg = _json_section("liquid_monitor")
    cfg: Dict[str, Any] = {}
    if isinstance(data, dict):
        cfg.update(data)
    if json_cfg:
        cfg.update(json_cfg)
    return LiquidationSettings(
        thresholds=cfg.get("thresholds", {}),
        blast_radius=cfg.get("blast_radius", {}),
        notifications=cfg.get("notifications", {}),
        enabled_liquid=cfg.get("enabled_liquid"),
    )


@router.post("/liquidation", status_code=status.HTTP_204_NO_CONTENT)
def post_liquidation_settings(
    payload: Dict[str, Any] = Body(...), dl: DataLocker = Depends(get_app_locker)
):
    if "threshold_percent" in payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="threshold_percent removed; set per-asset thresholds instead.",
        )

    normalized_payload = dict(payload)
    if "enabled" in normalized_payload and "enabled_liquid" not in normalized_payload:
        normalized_payload["enabled_liquid"] = normalized_payload.pop("enabled")

    thresholds_payload = dict(normalized_payload.get("thresholds") or {})
    legacy_threshold_keys = [key for key in list(normalized_payload.keys()) if key.startswith("threshold_") and key not in {"thresholds"}]
    for legacy_key in legacy_threshold_keys:
        value = normalized_payload.pop(legacy_key)
        asset = legacy_key.split("_", 1)[-1]
        if asset:
            thresholds_payload.setdefault(asset.upper(), value)
    if thresholds_payload:
        normalized_payload["thresholds"] = thresholds_payload

    notifications_payload = dict(normalized_payload.get("notifications") or {})
    for legacy_key, target in (
        ("windows_alert", "system"),
        ("voice_alert", "voice"),
        ("sms_alert", "sms"),
        ("tts_alert", "tts"),
    ):
        if legacy_key in normalized_payload:
            notifications_payload[target] = normalized_payload.pop(legacy_key)
    if notifications_payload:
        normalized_payload["notifications"] = notifications_payload

    try:
        model = LiquidationSettings(**normalized_payload)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors())

    shaped = _normalize_liq(model)
    try:
        save_config_patch({"liquid_monitor": shaped})
    except Exception:
        log.debug("Failed to persist liquidation config to JSON", exc_info=True)
    _dl_set_system_var(dl, "liquid_monitor", shaped)

    enabled_payload = {}
    if "enabled_liquid" in shaped:
        enabled_payload["liquid"] = shaped["enabled_liquid"]

    _persist_monitor_json(
        liquid={
            "thresholds": shaped.get("thresholds", {}),
            "blast": shaped.get("blast_radius", {}),
        },
        enabled=enabled_payload or None,
    )


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
    json_cfg = _json_section("market_monitor")
    cfg: Dict[str, Any] = {}
    if isinstance(data, dict):
        cfg.update(data)
    if json_cfg:
        cfg.update(json_cfg)
    return MarketSettings(
        thresholds=cfg.get("thresholds", {}),
        rearm_mode=cfg.get("rearm_mode"),
        notifications=cfg.get("notifications", {}),
        enabled_market=cfg.get("enabled_market"),
    )


@router.post("/market", status_code=status.HTTP_204_NO_CONTENT)
def post_market_settings(payload: MarketSettings, dl: DataLocker = Depends(get_app_locker)):
    shaped = _normalize_market(payload)
    try:
        save_config_patch({"market_monitor": shaped})
    except Exception:
        log.debug("Failed to persist market config to JSON", exc_info=True)
    _dl_set_system_var(dl, "market_monitor", shaped)

    enabled_payload = {}
    if "enabled_market" in shaped:
        enabled_payload["market"] = shaped["enabled_market"]
        enabled_payload["price"] = shaped["enabled_market"]

    _persist_monitor_json(enabled=enabled_payload or None)


# ------------------------------------------------------------------ #
# Profit Monitor thresholds (mirrors Liquid/Market schema)
# ------------------------------------------------------------------ #


class ProfitSettings(BaseModel):
    position_profit_usd: Any = 0
    portfolio_profit_usd: Any = 0
    notifications: Dict[str, bool] = Field(default_factory=dict)
    enabled_profit: Optional[bool] = None


def _bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _normalize_profit(payload: ProfitSettings) -> Dict[str, Any]:
    notifications = {"system": True, "voice": True, "sms": False, "tts": True}
    notifications.update(payload.notifications or {})

    cfg: Dict[str, Any] = {
        "position_profit_usd": float(_num(payload.position_profit_usd, 0.0) or 0.0),
        "portfolio_profit_usd": float(_num(payload.portfolio_profit_usd, 0.0) or 0.0),
        "notifications": {
            "system": _bool(notifications.get("system")),
            "voice": _bool(notifications.get("voice")),
            "sms": _bool(notifications.get("sms")),
            "tts": _bool(notifications.get("tts")),
        },
    }

    if payload.enabled_profit is not None:
        enabled = _bool(payload.enabled_profit)
        cfg["enabled_profit"] = enabled
        cfg["enabled"] = enabled

    return cfg


@router.get("/profit", response_model=ProfitSettings)
def get_profit_settings(dl: DataLocker = Depends(get_app_locker)):
    ts = ThresholdService(dl.db)
    portfolio_th = ts.get_thresholds("TotalProfit", "Portfolio", "ABOVE")
    single_th = ts.get_thresholds("Profit", "Position", "ABOVE")

    data = _dl_get_system_var(dl, "profit_monitor", {}) or {}
    json_cfg = _json_section("profit_monitor")
    cfg: Dict[str, Any] = {}
    if isinstance(data, dict):
        cfg.update(data)
    if json_cfg:
        cfg.update(json_cfg)

    position_value = cfg.get("position_profit_usd")
    if position_value in (None, ""):
        position_value = getattr(single_th, "high", 0.0) or 0.0

    portfolio_value = cfg.get("portfolio_profit_usd")
    if portfolio_value in (None, ""):
        portfolio_value = getattr(portfolio_th, "high", 0.0) or 0.0

    notifications = cfg.get("notifications", {})
    if not isinstance(notifications, dict):
        notifications = {
            "system": True,
            "voice": True,
            "sms": False,
            "tts": True,
        }

    enabled_profit = cfg.get("enabled_profit")
    if enabled_profit is None:
        enabled_profit = cfg.get("enabled")

    return ProfitSettings(
        position_profit_usd=position_value,
        portfolio_profit_usd=portfolio_value,
        notifications=notifications,
        enabled_profit=enabled_profit,
    )


@router.post("/profit", status_code=status.HTTP_204_NO_CONTENT)
def post_profit_settings(payload: ProfitSettings, dl: DataLocker = Depends(get_app_locker)):
    shaped = _normalize_profit(payload)

    try:
        save_config_patch({"profit_monitor": shaped})
    except Exception:
        log.debug("Failed to persist profit config to JSON", exc_info=True)

    _dl_set_system_var(dl, "profit_monitor", shaped)

    ts = ThresholdService(dl.db)
    try:
        ts.set_threshold("TotalProfit", "Portfolio", 0.0, shaped.get("portfolio_profit_usd"))
        ts.set_threshold("Profit", "Position", 0.0, shaped.get("position_profit_usd"))
    except Exception:
        log.debug("Failed to update profit thresholds", exc_info=True)

    enabled_payload = {}
    if "enabled_profit" in shaped:
        enabled_payload["profit"] = shaped["enabled_profit"]

    _persist_monitor_json(
        profit={
            "position_usd": shaped.get("position_profit_usd"),
            "portfolio_usd": shaped.get("portfolio_profit_usd"),
        },
        enabled=enabled_payload or None,
    )


__all__ = ["router"]
