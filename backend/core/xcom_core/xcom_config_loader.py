from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Tuple

# Prefer the correct filename, keep typo as fallback for safety
DEFAULT_FILENAMES = ("xcom_config.json", "xcom_congig.json")


def load_xcom_config(
    base_dir: Path | None = None,
    filename: str | None = None,
) -> Tuple[Dict[str, Any], Path | None]:
    """Load JSON config from disk.

    By default, look in the provided ``base_dir`` (or this file's directory).
    Try ``xcom_config.json`` first, then the legacy typo ``xcom_congig.json``
    for backwards compatibility.
    """

    base = base_dir or Path(__file__).parent
    candidates = [filename] if filename else list(DEFAULT_FILENAMES)

    for name in candidates:
        if not name:
            continue
        path = (base / name).resolve()
        if path.exists():
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            return data, path
    return {}, None


def _to_str(val: Any) -> str:
    if isinstance(val, bool):
        return "1" if val else "0"
    return str(val)


def apply_xcom_env(cfg: Dict[str, Any]) -> Dict[str, str]:
    """Map JSON keys to environment variables used by XCom/Twilio paths."""

    mapping = {
        "SONIC_XCOM_LIVE": "SONIC_XCOM_LIVE",
        # Canonical Twilio credentials
        "TWILIO_ACCOUNT_SID": "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN": "TWILIO_AUTH_TOKEN",
        # Canonical phone numbers
        "TWILIO_FROM_PHONE": "TWILIO_FROM_PHONE",
        "TWILIO_TO_PHONE": "TWILIO_TO_PHONE",
        # Legacy aliases for compatibility
        "TWILIO_FROM": "TWILIO_FROM_PHONE",
        "TWILIO_TO": "TWILIO_TO_PHONE",
        "TWILIO_PHONE_NUMBER": "TWILIO_FROM_PHONE",
        "MY_PHONE_NUMBER": "TWILIO_TO_PHONE",
        "TWILIO_SID": "TWILIO_ACCOUNT_SID",
        # Textbelt + ngrok metadata used by the console/router
        "PUBLIC_BASE_URL": "PUBLIC_BASE_URL",
        "TEXTBELT_REPLY_WEBHOOK_URL": "TEXTBELT_REPLY_WEBHOOK_URL",
        "TEXTBELT_WEBHOOK_SECRET": "TEXTBELT_WEBHOOK_SECRET",
        "TEXTBELT_KEY": "TEXTBELT_KEY",
        "TEXTBELT_ENDPOINT": "TEXTBELT_ENDPOINT",
        "TEXTBELT_DEFAULT_TO": "TEXTBELT_DEFAULT_TO",
        # Inbox path (Textbelt replies JSONL)
        "XCOM_INBOUND_LOG": "XCOM_INBOUND_LOG",
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
        if "TOKEN" in key or key.endswith("_SID"):
            if isinstance(value, str) and len(value) > 8:
                masked[key] = value[:4] + "…" + value[-4:]
            else:
                masked[key] = "****"
        elif "PHONE" in key or key.endswith("_NUMBER"):
            masked[key] = value  # phone numbers are safe to show
        else:
            masked[key] = value
    return masked
