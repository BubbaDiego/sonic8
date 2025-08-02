import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from flask import current_app, has_app_context
except Exception:  # pragma: no cover - optional dependency
    current_app = type("obj", (), {})()

    def has_app_context():  # pragma: no cover - simple stub
        return False
from core.logging import log
from backend.utils.env_utils import _resolve_env

ENV_MAP = {
    "email": {
        "smtp": {
            "server": "SMTP_SERVER",
            "port": "SMTP_PORT",
            "username": "SMTP_USERNAME",
            "password": "SMTP_PASSWORD",
            "default_recipient": "SMTP_DEFAULT_RECIPIENT",
        }
    },
    "twilio": {
        "account_sid": "TWILIO_ACCOUNT_SID",
        "auth_token": "TWILIO_AUTH_TOKEN",
        "flow_sid": "TWILIO_FLOW_SID",
        "default_to_phone": "MY_PHONE_NUMBER",
        "default_from_phone": "TWILIO_PHONE_NUMBER",
    },
    "alexa": {
        "enabled": "ALEXA_ENABLED",
        "access_code": "ALEXA_ACCESS_CODE",
    },
}

class XComConfigService:
    def __init__(self, dl_sys):
        # dl_sys may be either a DataLocker or its DLSystemDataManager.
        # It is stored for use when a Flask ``current_app`` context is not
        # available.
        self.dl_sys = dl_sys

    def get_provider(self, name: str) -> dict:
        try:
            locker = None
            if has_app_context():
                locker = getattr(current_app, "data_locker", None)

            if not locker or not hasattr(locker, "system"):
                if hasattr(self.dl_sys, "get_var"):
                    system_mgr = self.dl_sys
                elif hasattr(self.dl_sys, "system") and hasattr(self.dl_sys.system, "get_var"):
                    system_mgr = self.dl_sys.system
                else:
                    raise Exception("data_locker.system not available")
            else:
                system_mgr = locker.system

            config = system_mgr.get_var("xcom_providers") or {}
            provider_name = "twilio" if name == "api" else name
            provider = config.get(provider_name) or {}

            # Explicitly fallback to environment vars for Twilio ("api")
            if provider_name == "twilio" and (not provider or not provider.get("account_sid")):
                provider = {
                    "enabled": True,
                    "account_sid": os.getenv("TWILIO_ACCOUNT_SID"),
                    "auth_token": os.getenv("TWILIO_AUTH_TOKEN"),
                    "flow_sid": os.getenv("TWILIO_FLOW_SID"),
                    "default_to_phone": os.getenv("MY_PHONE_NUMBER"),
                    "default_from_phone": os.getenv("TWILIO_PHONE_NUMBER"),
                }

            def apply_env(data: dict, mapping: dict) -> dict:
                for k, v in list(data.items()):
                    sub_map = mapping.get(k, {}) if isinstance(mapping, dict) else {}
                    if isinstance(v, dict):
                        data[k] = apply_env(v, sub_map if isinstance(sub_map, dict) else {})
                    else:
                        env_key = sub_map if isinstance(sub_map, str) else None
                        data[k] = _resolve_env(v, env_key)
                return data

            env_map = ENV_MAP.get(provider_name, {})
            if isinstance(provider, dict):
                provider = apply_env(provider, env_map)

            return provider
        except Exception as e:
            log.error(f"Failed to load provider config for '{name}': {e}", source="XComConfigService")
            return {}
