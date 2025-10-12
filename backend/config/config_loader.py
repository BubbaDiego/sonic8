from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

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
