from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Default JSON path: <repo_root>/backend/data/sonic_config.json
DEFAULT_JSON_PATH = Path(__file__).resolve().parents[1] / "backend" / "data" / "sonic_config.json"


def _expand_env(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _expand_env(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_env(v) for v in obj]
    if isinstance(obj, str):
        return os.path.expandvars(obj)
    return obj


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return _expand_env(data or {})
    except Exception:
        return {}


def _atomic_write(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data or {}, f, indent=2, sort_keys=True)
    tmp.replace(path)


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """
    Minimal loader used by OperationsMonitor and friends.
    Reads a JSON config file and expands ${ENV_VARS} inside string values.
    """
    p = Path(path) if path else DEFAULT_JSON_PATH
    if not p.exists():
        return {}
    return _read_json(p)


def save_config(data: Dict[str, Any], path: Optional[str] = None) -> Path:
    """
    Minimal saver for tools that want to persist config.
    """
    p = Path(path) if path else DEFAULT_JSON_PATH
    _atomic_write(p, data or {})
    return p
