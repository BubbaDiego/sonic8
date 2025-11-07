from __future__ import annotations

import os
import json
from typing import Optional, Dict, Any, Tuple

# If set, this env var can carry a full JSON blob to overlay.
ENV_JSON = "SONIC_MONITOR_JSON"


def read_overlay() -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Read-only overlay from environment.
    Lowest priority by default (JSON/DB override it).
    Supports:
      - SONIC_MONITOR_JSON = '{...}'
      - SONIC_MONITOR_LOOP_SECONDS = '30'
      - SONIC_MONITOR_XCOM_LIVE = 'true'/'false'
    """
    raw = os.environ.get(ENV_JSON)
    if raw:
        try:
            return json.loads(raw), ENV_JSON
        except Exception:
            return None, ENV_JSON

    overlay: Dict[str, Any] = {}

    if "SONIC_MONITOR_LOOP_SECONDS" in os.environ:
        try:
            val = float(os.environ["SONIC_MONITOR_LOOP_SECONDS"])
            overlay.setdefault("monitor", {})["loop_seconds"] = val
        except Exception:
            pass

    if "SONIC_MONITOR_XCOM_LIVE" in os.environ:
        val = os.environ["SONIC_MONITOR_XCOM_LIVE"].strip().lower() in ("1", "true", "yes", "on")
        overlay.setdefault("monitor", {})["xcom_live"] = val

    return (overlay if overlay else None), "ENV"
