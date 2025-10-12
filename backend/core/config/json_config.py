"""Utility helpers for reading and writing the shared Sonic JSON config."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict

CONFIG_ENV_VAR = "SONIC_CONFIG_JSON_PATH"
DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "sonic_config.json"


def _config_path() -> Path:
    """Return the path to the Sonic JSON configuration file."""

    env_path = os.getenv(CONFIG_ENV_VAR)
    if env_path:
        return Path(env_path)
    return DEFAULT_PATH


def _expand_env(obj: Any) -> Any:
    """Recursively expand ``${VAR}`` references within strings."""

    if isinstance(obj, dict):
        return {key: _expand_env(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_expand_env(value) for value in obj]
    if isinstance(obj, str):
        return os.path.expandvars(obj)
    return obj


def load_config() -> Dict[str, Any]:
    """Load the JSON configuration, expanding environment variables."""

    path = _config_path()
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return {}

    return _expand_env(data)


def _deep_merge(destination: dict, source: dict) -> dict:
    """Recursively merge ``source`` into ``destination`` without mutating either."""

    merged: dict = dict(destination)
    for key, value in source.items():
        if (
            isinstance(value, dict)
            and isinstance(merged.get(key), dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def save_config_patch(patch: Dict[str, Any]) -> Path:
    """Persist ``patch`` into the JSON file atomically and return the final path."""

    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    current = load_config()
    merged = _deep_merge(current, patch)

    fd, tmp_name = tempfile.mkstemp(
        prefix="sonic_cfg.", suffix=".json", dir=str(path.parent)
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(merged, handle, indent=2, sort_keys=True)
        shutil.move(str(tmp_path), str(path))
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass

    return path


def get_path_str() -> str:
    """Return the resolved configuration path as a string for diagnostics."""

    return str(_config_path())


__all__ = [
    "CONFIG_ENV_VAR",
    "DEFAULT_PATH",
    "get_path_str",
    "load_config",
    "save_config_patch",
]

