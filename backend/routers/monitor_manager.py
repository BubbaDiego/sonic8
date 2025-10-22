"""Monitor configuration management routes."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from backend.data.data_locker import DataLocker
from backend.data.dl_system_data import DLSystemDataManager
from backend.config.config_loader import (
    load_monitor_config,
    _deep_merge_dict_inplace,
    _atomic_write_json,
)

router = APIRouter(prefix="/api/monitor", tags=["monitor-config"])


def _json_path() -> str:
    """Return the JSON config path, defaulting to config/sonic_monitor_config.json."""

    here = Path(__file__).resolve()
    root = here.parents[2] if "backend" in here.parts else here.parents[1]
    return os.getenv("SONIC_MONITOR_CONFIG_PATH") or str(
        root / "config" / "sonic_monitor_config.json"
    )


def _expand_env(node: Any) -> Any:
    """Recursively expand environment variables in ${VAR} strings."""

    if isinstance(node, str):
        match = re.fullmatch(r"\$\{([^}]+)\}", node.strip())
        return os.getenv(match.group(1), node) if match else node
    if isinstance(node, list):
        return [_expand_env(item) for item in node]
    if isinstance(node, dict):
        return {key: _expand_env(value) for key, value in node.items()}
    return node


def _load_json_cfg() -> Dict:
    """Load the monitor JSON config file (if present)."""

    path = _json_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as file:
            return _expand_env(json.load(file) or {}) or {}
    except Exception:
        return {}


def _save_json_cfg(patch: Dict[str, Any]) -> Dict[str, Any]:
    """Patch-merge monitor settings into JSON and write atomically."""

    cfg, path = load_monitor_config()
    _deep_merge_dict_inplace(cfg, patch or {})

    profit = cfg.setdefault("profit", {})
    if profit.get("snooze_seconds") is None:
        profit["snooze_seconds"] = 600
    if profit.get("position_usd") is None:
        profit["position_usd"] = 0
    if profit.get("portfolio_usd") is None:
        profit["portfolio_usd"] = 0

    cfg.setdefault("price", {}).setdefault("assets", ["BTC", "ETH", "SOL"])

    _atomic_write_json(Path(path), cfg)
    return cfg


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).lower() in {"1", "true", "yes", "on"}


def _coerce_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(float(value))


def _coerce_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


# DB keys the monitors read today
_DB_KEYS = {
    "loop_time": "sonic_monitor_loop_time",  # legacy loop key monitor already uses
    "alert_thresholds": "alert_thresholds",  # {"thresholds": {...}, "blast": {...}}
    "profit_pos": "profit_pos",
    "profit_pf": "profit_pf",
    "profit_badge_value": "profit_badge_value",  # alias for some readers
    "xcom_providers": "xcom_providers",  # per-monitor channel toggles
    "market_monitor": "market_monitor",  # blob of market config
}


@router.get("/config")
def get_monitor_config() -> Dict[str, Any]:
    """Return the merged monitor configuration."""

    # Load JSON (primary)
    json_payload = _load_json_cfg()

    # DB fallback
    root = Path(__file__).resolve().parents[2]
    db_path = os.getenv("SONIC_DB_PATH") or str(root / "mother.db")
    dal = DataLocker.get_instance(db_path)
    sysmgr = DLSystemDataManager(dal.db)

    # loop delay
    loop_json = (
        json_payload.get("system_config", {}).get("sonic_loop_delay")
        or json_payload.get("monitor", {}).get("loop_seconds")
        or json_payload.get("system_config", {}).get("sonic_monitor_loop_time")
    )
    loop_db = sysmgr.get_var(_DB_KEYS["loop_time"])
    loop_env = os.getenv("SONIC_MONITOR_LOOP_SECONDS")
    loop = (
        _coerce_int(loop_json)
        or _coerce_int(loop_db)
        or _coerce_int(loop_env)
        or 60
    )

    # liquid thresholds
    thr_json = (
        json_payload.get("liquid_monitor", {}).get("thresholds")
        or json_payload.get("liquid", {}).get("thresholds")
        or {}
    )
    blast_json = json_payload.get("liquid", {}).get("blast") or {}
    thr_db_payload = sysmgr.get_var(_DB_KEYS["alert_thresholds"]) or "{}"
    try:
        thr_db_data = json.loads(thr_db_payload)
        thr_db = thr_db_data.get("thresholds") or {}
        blast_db = thr_db_data.get("blast") or {}
    except Exception:
        thr_db, blast_db = {}, {}

    def _thr_for(symbol: str) -> float | None:
        return _coerce_float(thr_json.get(symbol)) or _coerce_float(thr_db.get(symbol))

    def _blast_for(symbol: str) -> int:
        value = blast_json.get(symbol, blast_db.get(symbol, 0))
        return _coerce_int(value) or 0

    # profit thresholds
    pos_json = json_payload.get("profit", {}).get("position_usd")
    pf_json = json_payload.get("profit", {}).get("portfolio_usd")
    pos = _coerce_int(pos_json) or _coerce_int(sysmgr.get_var(_DB_KEYS["profit_pos"]))
    pf = _coerce_int(pf_json) or _coerce_int(sysmgr.get_var(_DB_KEYS["profit_pf"]))
    if pf is None:
        pf = _coerce_int(sysmgr.get_var(_DB_KEYS["profit_badge_value"]))

    # channels
    raw_channels = json_payload.get("channels") or {}
    if not isinstance(raw_channels, dict):
        raw_channels = {}
    if not raw_channels:
        legacy_global = json_payload.get("xcom", {}).get("channels", {})
        raw_channels = {"global": legacy_global}
        for monitor_key in ("price", "liquid", "profit", "market"):
            monitor_cfg = json_payload.get(monitor_key, {})
            if isinstance(monitor_cfg, dict) and monitor_cfg.get("notifications"):
                raw_channels[monitor_key] = monitor_cfg["notifications"]

    try:
        db_channels = json.loads(sysmgr.get_var(_DB_KEYS["xcom_providers"]) or "{}")
    except Exception:
        db_channels = {}

    json_global = raw_channels.get("global") if isinstance(raw_channels.get("global"), dict) else {}
    db_global = db_channels.get("global") if isinstance(db_channels.get("global"), dict) else {}

    def _norm_channels(cfg: dict | None, fallback: dict | None):
        merged = {"system": True, "voice": False, "sms": False, "tts": False}
        for source in (db_global, json_global, fallback, cfg):
            if not isinstance(source, dict):
                continue
            for key in merged:
                if key in source:
                    merged[key] = _coerce_bool(source.get(key), merged[key])
        return merged

    merged_channels = {
        monitor: _norm_channels(raw_channels.get(monitor), db_channels.get(monitor))
        for monitor in ("price", "liquid", "profit", "market")
    }

    # market blob
    try:
        db_market = json.loads(sysmgr.get_var(_DB_KEYS["market_monitor"]) or "{}")
    except Exception:
        db_market = {}
    market = json_payload.get("market") or db_market

    # assets
    assets = (
        json_payload.get("price_config", {}).get("assets")
        or json_payload.get("price", {}).get("assets")
        or ["BTC", "ETH", "SOL"]
    )

    return {
        "source": {"primary": "JSON", "path": _json_path()},
        "monitor": {"loop_seconds": loop},
        "assets": assets,
        "liquid": {
            "thresholds": {symbol: _thr_for(symbol) for symbol in assets},
            "blast": {symbol: _blast_for(symbol) for symbol in assets},
        },
        "profit": {
            "position_usd": pos,
            "portfolio_usd": pf,
        },
        "channels": merged_channels,
        "market": market,
    }


@router.post("/config")
def save_monitor_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Persist the provided monitor configuration to DB and JSON."""

    if not isinstance(payload, dict):  # defensive guard
        raise HTTPException(status_code=400, detail="Payload must be an object")

    if "threshold_percent" in (payload.get("liquid") or {}):
        raise HTTPException(
            status_code=400,
            detail="threshold_percent removed; set per-asset thresholds instead.",
        )

    root = Path(__file__).resolve().parents[2]
    db_path = os.getenv("SONIC_DB_PATH") or str(root / "mother.db")
    dal = DataLocker.get_instance(db_path)
    sysmgr = DLSystemDataManager(dal.db)

    # loop
    monitor_payload = payload.get("monitor", {}) or {}
    loop = _coerce_int(monitor_payload.get("loop_seconds"))
    if loop is not None:
        sysmgr.set_var(_DB_KEYS["loop_time"], loop)

    # liquid
    liquid_payload = payload.get("liquid", {}) or {}
    thresholds = liquid_payload.get("thresholds") or {}
    blast = liquid_payload.get("blast") or {}
    thr_clean = {
        str(symbol).upper(): _coerce_float(value)
        for symbol, value in thresholds.items()
        if _coerce_float(value) is not None
    }
    blast_clean = {
        str(symbol).upper(): _coerce_int(blast.get(symbol)) or 0 for symbol in thresholds.keys()
    }
    sysmgr.set_var(
        _DB_KEYS["alert_thresholds"],
        json.dumps({"thresholds": thr_clean, "blast": blast_clean}, separators=(",", ":")),
    )

    # profit
    pos = _coerce_int(payload.get("profit", {}).get("position_usd"))
    pf = _coerce_int(payload.get("profit", {}).get("portfolio_usd"))
    if pos is not None:
        sysmgr.set_var(_DB_KEYS["profit_pos"], pos)
    if pf is not None:
        sysmgr.set_var(_DB_KEYS["profit_pf"], pf)
        sysmgr.set_var(_DB_KEYS["profit_badge_value"], pf)

    # channels
    channels_payload = payload.get("channels") or {}
    sysmgr.set_var(
        _DB_KEYS["xcom_providers"],
        json.dumps(channels_payload, separators=(",", ":")),
    )

    # market
    market_payload = payload.get("market") or {}
    sysmgr.set_var(
        _DB_KEYS["market_monitor"],
        json.dumps(market_payload, separators=(",", ":")),
    )

    patch: Dict[str, Any] = {}

    sonic = payload.get("system_config") or {}
    if "sonic_loop_delay" in sonic:
        try:
            delay = int(sonic["sonic_loop_delay"])
        except (TypeError, ValueError):
            delay = None
        if delay is not None:
            patch.setdefault("monitor", {})["loop_seconds"] = delay
            patch.setdefault("system_config", {})["sonic_loop_delay"] = delay
    elif loop is not None:
        patch.setdefault("monitor", {})["loop_seconds"] = loop
        patch.setdefault("system_config", {})["sonic_loop_delay"] = loop

    if "live" in sonic:
        patch.setdefault("monitor", {})["xcom_live"] = bool(sonic["live"])
    elif "xcom_live" in monitor_payload:
        patch.setdefault("monitor", {})["xcom_live"] = bool(monitor_payload["xcom_live"])

    assets_payload = payload.get("assets")
    if isinstance(assets_payload, list):
        patch.setdefault("price", {})["assets"] = assets_payload

    if thresholds:
        patch.setdefault("liquid", {})["thresholds"] = thr_clean
    if blast:
        patch.setdefault("liquid", {})["blast"] = blast_clean

    liq_notifications = liquid_payload.get("notifications")
    if isinstance(liq_notifications, dict):
        patch.setdefault("channels", {}).setdefault("liquid", {}).update(liq_notifications)

    profit_payload = payload.get("profit")
    if isinstance(profit_payload, dict):
        profit_patch: Dict[str, Any] = {}
        if profit_payload.get("position_usd") is not None:
            pos_val = _coerce_int(profit_payload.get("position_usd"))
            if pos_val is not None:
                profit_patch["position_usd"] = pos_val
        if profit_payload.get("portfolio_usd") is not None:
            pf_val = _coerce_int(profit_payload.get("portfolio_usd"))
            if pf_val is not None:
                profit_patch["portfolio_usd"] = pf_val
        if profit_payload.get("snooze_seconds") is not None:
            snooze_val = _coerce_int(profit_payload.get("snooze_seconds"))
            if snooze_val is not None:
                profit_patch["snooze_seconds"] = snooze_val
        if profit_patch:
            patch["profit"] = profit_patch

    if isinstance(channels_payload, dict):
        channels_patch = patch.setdefault("channels", {})
        for key, value in channels_payload.items():
            if (
                isinstance(value, dict)
                and isinstance(channels_patch.get(key), dict)
            ):
                channels_patch.setdefault(key, {}).update(value)
            else:
                channels_patch[key] = value

    if isinstance(market_payload, dict) and market_payload:
        patch.setdefault("market", {}).update(market_payload)

    cfg = _save_json_cfg(patch)

    return {"ok": True, "config": cfg}
