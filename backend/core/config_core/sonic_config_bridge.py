from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional, List

try:
    # Correct import path per repo layout
    from backend.config.config_loader import load_config
except Exception:
    # Last-ditch fallback if module is executed differently
    from config_loader import load_config  # type: ignore

_CFG: Dict[str, Any] = {}
_LOADED: bool = False


def load(path: Optional[str] = None) -> Dict[str, Any]:
    global _CFG, _LOADED
    if not _LOADED:
        # Default to backend/config/sonic_config.json unless overridden by env
        cfg_path = (
            path
            or os.getenv("SONIC_CONFIG_JSON_PATH")
            or str(Path(__file__).resolve().parents[3] / "backend" / "config" / "sonic_config.json")
        )
        _CFG = load_config(cfg_path) or {}
        _LOADED = True
    return _CFG


def get_loop_seconds() -> Optional[int]:
    cfg = load()
    try:
        value = cfg.get("system_config", {}).get("sonic_monitor_loop_time")
        return int(value) if value is not None else None
    except Exception:
        return None


def get_db_path() -> Optional[str]:
    cfg = load()
    return cfg.get("system_config", {}).get("db_path") or None


def get_price_assets() -> List[str]:
    cfg = load()
    assets = cfg.get("price_config", {}).get("assets") or []
    normalized = [str(asset).upper() for asset in assets if str(asset).strip()]
    return normalized or ["BTC", "ETH", "SOL"]


def get_twilio() -> Dict[str, str]:
    cfg = load().get("twilio_config", {}) or {}
    return {
        "SID": str(cfg.get("account_sid") or ""),
        "AUTH": str(cfg.get("auth_token") or ""),
        "FLOW": str(cfg.get("flow_sid") or ""),
        "FROM": str(cfg.get("from_phone") or ""),
        "TO": str(cfg.get("to_phone") or ""),
    }


def get_liquid_thresholds() -> Dict[str, float]:
    cfg = load()
    thresholds = cfg.get("liquid_monitor", {}).get("thresholds") or {}
    output: Dict[str, float] = {}
    for key, value in thresholds.items():
        try:
            output[str(key).upper()] = float(value)
        except Exception:
            pass
    return output
