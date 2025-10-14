from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Tuple

DEFAULT_FILENAMES = ("xcom_congig.json", "xcom_config.json")  # tries your exact name first


def load_xcom_config(base_dir: Path | None = None, filename: str | None = None) -> Tuple[Dict[str, Any], Path | None]:
    """Loads JSON config from the console app's local directory by default.

    Tries xcom_congig.json first, then xcom_config.json (typo-friendly).
    """
    base = base_dir or Path(__file__).parent
    candidates = [filename] if filename else list(DEFAULT_FILENAMES)
    for name in candidates:
        if not name:
            continue
        path = (base / name).resolve()
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data, path
    return {}, None


def _to_str(val: Any) -> str:
    if isinstance(val, bool):
        return "1" if val else "0"
    return str(val)


def apply_xcom_env(cfg: Dict[str, Any]) -> Dict[str, str]:
    """Maps JSON keys to environment names that the rest of the stack expects."""
    mapping = {
        "SONIC_XCOM_LIVE": "SONIC_XCOM_LIVE",
        "TWILIO_SID": "TWILIO_SID",
        "TWILIO_AUTH_TOKEN": "TWILIO_AUTH_TOKEN",
        "TWILIO_FLOW_SID": "TWILIO_FLOW_SID",
        # Normalize to the env names existing code already reads:
        "TWILIO_FROM": "TWILIO_PHONE_NUMBER",
        "TWILIO_TO": "MY_PHONE_NUMBER",
    }

    effective: Dict[str, str] = {}
    for src_key, env_key in mapping.items():
        if src_key in cfg and cfg[src_key] is not None:
            os.environ[env_key] = _to_str(cfg[src_key])
            effective[env_key] = os.environ[env_key]
    return effective


def mask_for_log(effective_env: Dict[str, str]) -> Dict[str, str]:
    masked: Dict[str, str] = {}
    for key, value in effective_env.items():
        if "TOKEN" in key or "SID" in key:
            if len(value) > 8:
                masked[key] = value[:4] + "…" + value[-4:]
            else:
                masked[key] = "****"
        elif "PHONE" in key or key.endswith("_NUMBER"):
            masked[key] = value  # phone numbers are fine to show
        else:
            masked[key] = value
    return masked
