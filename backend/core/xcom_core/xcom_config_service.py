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


def _resolve_env(value, env_key):
    """Return the value or fallback to environment variable if empty or a placeholder."""
    if value is None or value == "":
        return os.getenv(env_key)
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return os.getenv(value[2:-1])
    return value

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
            # Fallback to the object passed into ``__init__`` when Flask
            # context is unavailable. ``self.dl_sys`` can be either a
            # DataLocker instance or already the DLSystemDataManager.
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
            # Recognize 'api' as an alias for the 'twilio' provider
            provider = config.get(name) or (config.get("twilio") if name == "api" else {})
            # Fallback for email if missing/empty
            if name == "email" and (not provider or not provider.get("smtp")):
                provider = {
                    "enabled": True,
                    "smtp": {
                        "server": os.getenv("SMTP_SERVER"),
                        "port": int(os.getenv("SMTP_PORT", "0")) if os.getenv("SMTP_PORT") else None,
                        "username": os.getenv("SMTP_USERNAME"),
                        "password": os.getenv("SMTP_PASSWORD"),
                        "default_recipient": os.getenv("SMTP_DEFAULT_RECIPIENT"),
                    },
                }

            # Fallback for API (Twilio) if missing/empty. "api" is treated
            # as an alias for the "twilio" provider above.
            if name == "api" and not provider:
                provider = {
                    "enabled": True,
                    "account_sid": os.getenv("TWILIO_ACCOUNT_SID"),
                    "auth_token": os.getenv("TWILIO_AUTH_TOKEN"),
                    "flow_sid": os.getenv("TWILIO_FLOW_SID"),
                    "default_to_phone": os.getenv("MY_PHONE_NUMBER"),
                    "default_from_phone": os.getenv("TWILIO_PHONE_NUMBER"),
                }

            # Resolve placeholders using environment variables
            if name == "email":
                smtp = provider.get("smtp", {})
                smtp["server"] = _resolve_env(smtp.get("server"), "SMTP_SERVER")
                port_val = _resolve_env(smtp.get("port"), "SMTP_PORT")
                smtp["port"] = int(port_val) if port_val else None
                smtp["username"] = _resolve_env(smtp.get("username"), "SMTP_USERNAME")
                smtp["password"] = _resolve_env(smtp.get("password"), "SMTP_PASSWORD")
                smtp["default_recipient"] = _resolve_env(smtp.get("default_recipient"), "SMTP_DEFAULT_RECIPIENT")
                provider["smtp"] = smtp

            if name == "api":
                provider["account_sid"] = _resolve_env(provider.get("account_sid"), "TWILIO_ACCOUNT_SID")
                provider["auth_token"] = _resolve_env(provider.get("auth_token"), "TWILIO_AUTH_TOKEN")
                provider["flow_sid"] = _resolve_env(provider.get("flow_sid"), "TWILIO_FLOW_SID")
                provider["default_to_phone"] = _resolve_env(provider.get("default_to_phone"), "MY_PHONE_NUMBER")
                provider["default_from_phone"] = _resolve_env(provider.get("default_from_phone"), "TWILIO_PHONE_NUMBER")

            return provider
        except Exception as e:
            log.error(f"Failed to load provider config for '{name}': {e}", source="XComConfigService")
            return {}

