from __future__ import annotations

import importlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

ALERT_THRESHOLDS_PATH: Path
_spec = importlib.util.find_spec("backend.core.core_constants")
if _spec is not None:
    _module = importlib.import_module("backend.core.core_constants")
    ALERT_THRESHOLDS_PATH = Path(
        getattr(
            _module,
            "ALERT_THRESHOLDS_PATH",
            Path(__file__).resolve().parents[1] / "config" / "alert_thresholds.json",
        )
    )
else:
    ALERT_THRESHOLDS_PATH = Path(__file__).resolve().parents[1] / "config" / "alert_thresholds.json"


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
            return json.load(f) or {}
    except Exception:
        return {}


def _atomic_write(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    tmp.replace(path)


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    """
    Read a JSON config file and expand environment variables inside string values.
    Mirrors the simple usage expected by OperationsMonitor.
    """

    config_path = Path(path) if path else ALERT_THRESHOLDS_PATH
    if not config_path.exists():
        return {}
    return _expand_env(_read_json(config_path))


def save_config(data: Dict[str, Any], path: Optional[str] = None) -> Path:
    """Write a JSON config file atomically."""

    config_path = Path(path) if path else ALERT_THRESHOLDS_PATH
    _atomic_write(config_path, data or {})
    return config_path
