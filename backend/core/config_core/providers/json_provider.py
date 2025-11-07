from __future__ import annotations

import os
import json
import time
from typing import Optional, Dict, Any, Tuple

# Resolve repo root from this file, then default to backend/config/sonic_monitor_config.json
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
DEFAULT_JSON_PATH = os.path.join(REPO_ROOT, "backend", "config", "sonic_monitor_config.json")


def read_config(path: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    p = path or DEFAULT_JSON_PATH
    try:
        if not os.path.exists(p):
            return None, p
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f), p
    except Exception:
        return None, p


def write_config(cfg: Dict[str, Any], path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    p = path or DEFAULT_JSON_PATH
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        # rotate a timestamped backup if a file already exists
        if os.path.exists(p):
            ts = time.strftime("%Y%m%d_%H%M%S")
            os.replace(p, p + f".bak_{ts}")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True, p
    except Exception:
        return False, p
