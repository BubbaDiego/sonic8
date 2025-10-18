from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config.config_loader import load_config_json_only

_CFG: Dict[str, Any] | None = None
CFG_PATH = Path(__file__).resolve().parents[2] / "config" / "sonic_monitor_config.json"


def load() -> Dict[str, Any]:
    """
    Temporary: JSON-only path (no env/DB). Revert to load_config(...) later.
    """

    global _CFG
    if _CFG is None:
        _CFG = load_config_json_only(str(CFG_PATH))
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
