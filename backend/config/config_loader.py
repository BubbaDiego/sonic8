from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


# === Monitor config (JSON) ==============================================
def _mon_cfg_default_path() -> str:
    """Return the default on-disk location for the monitor JSON file."""

    here = Path(__file__).resolve()
    return str(here.parent / "sonic_monitor_config.json")


def load_monitor_config(path: str | None = None) -> dict:
    """Load ``sonic_monitor_config.json`` (or an override from the environment)."""

    cfg_path = path or os.getenv("SONIC_MONITOR_CONFIG_PATH") or _mon_cfg_default_path()
    try:
        with open(cfg_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_monitor_config(data: dict, path: str | None = None) -> bool:
    """Persist the monitor configuration JSON atomically."""

    if not isinstance(data, dict):
        return False

    cfg_path = path or os.getenv("SONIC_MONITOR_CONFIG_PATH") or _mon_cfg_default_path()
    try:
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        tmp_path = f"{cfg_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
        os.replace(tmp_path, cfg_path)
        return True
    except Exception:
        return False

# Default JSON at repo_root/backend/data/sonic_config.json
_DEFAULT = Path(__file__).resolve().parents[1] / "data" / "sonic_config.json"
_ENV_VAR = "SONIC_CONFIG_JSON_PATH"  # optional override


def _expand_env(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _expand_env(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env(v) for v in obj]
    if isinstance(obj, str):
        return os.path.expandvars(obj)
    return obj


def _path(custom: Optional[str]) -> Path:
    if custom:
        return Path(custom)
    env_path = os.getenv(_ENV_VAR)
    return Path(env_path) if env_path else _DEFAULT


def load_config(filename: Optional[str] = None) -> Dict[str, Any]:
    """Read config JSON (expands ${ENV} in strings)."""

    config_path = _path(filename)
    try:
        with config_path.open("r", encoding="utf-8") as f:
            return _expand_env(json.load(f) or {})
    except Exception:
        return {}
