from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Default JSON at repo root → backend/data/sonic_config.json
_DEFAULT_JSON_PATH = Path(__file__).resolve().parents[1] / "backend" / "data" / "sonic_config.json"
_ENV_VAR = "SONIC_CONFIG_JSON_PATH"  # optional override


def _cfg_path(path: Optional[str] = None) -> Path:
    if path:
        return Path(path)
    env = os.getenv(_ENV_VAR)
    return Path(env) if env else _DEFAULT_JSON_PATH


def _expand_env(v: Any) -> Any:
    if isinstance(v, dict):
        return {k: _expand_env(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_expand_env(x) for x in v]
    if isinstance(v, str):
        return os.path.expandvars(v)
    return v


def _read_json(p: Path) -> Dict[str, Any]:
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f) or {}
        return _expand_env(data)
    except Exception:
        return {}


def _atomic_write(p: Path, data: Dict[str, Any]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data or {}, f, indent=2, sort_keys=True)
    tmp.replace(p)


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """Read sonic JSON config (expands ${ENV} inside strings)."""
    p = _cfg_path(path)
    return _read_json(p) if p.exists() else {}


def save_config(data: Dict[str, Any], path: Optional[str] = None) -> Path:
    """Atomically write sonic JSON config."""
    p = _cfg_path(path)
    _atomic_write(p, data or {})
    return p


def get_default_path() -> str:
    return str(_cfg_path(None))
