# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict

DEFAULT_JSON_PATH = str(Path(__file__).resolve().parents[2] / "config" / "sonic_monitor_config.json")


def _json_path() -> str:
    return os.getenv("SONIC_MONITOR_CONFIG_PATH") or DEFAULT_JSON_PATH


def read_monitor_config() -> Dict[str, Any]:
    path = _json_path()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle) or {}
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}
