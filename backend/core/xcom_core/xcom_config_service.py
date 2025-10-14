import json
import sys
import os
from copy import deepcopy

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
        "flow_sid": ["TWILIO_FLOW_SID", "TWILIO_STUDIO_FLOW_SID"],
        "default_to_phone": [
            "MY_PHONE_NUMBER",
            "TWILIO_TO_PHONE",
            "TWILIO_DEFAULT_TO_PHONE",
        ],
        "default_from_phone": [
            "TWILIO_PHONE_NUMBER",
            "TWILIO_FROM_PHONE",
            "TWILIO_DEFAULT_FROM_PHONE",
        ],
        "use_studio": None,
        "speak_plain": "TWILIO_SPEAK_PLAIN",
    },
    "sms": {
        "sid": "TWILIO_ACCOUNT_SID",
        "token": "TWILIO_AUTH_TOKEN",
        "from_number": ["TWILIO_FROM_PHONE", "TWILIO_PHONE_NUMBER"],
        "default_recipient": ["TWILIO_TO_PHONE", "MY_PHONE_NUMBER"],
        "carrier_gateway": "SMS_CARRIER_GATEWAY",
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

    def _resolve_system_manager(self):
        locker = None
        if has_app_context():
            locker = getattr(current_app, "data_locker", None)

        if locker and hasattr(locker, "system"):
            return locker.system

        if hasattr(self.dl_sys, "get_var"):
            return self.dl_sys

        if hasattr(self.dl_sys, "system") and hasattr(self.dl_sys.system, "get_var"):
            return self.dl_sys.system

        raise Exception("data_locker.system not available")

    def _load_providers(self) -> dict:
        try:
            system_mgr = self._resolve_system_manager()
            config = system_mgr.get_var("xcom_providers") or {}
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                except Exception:
                    config = {}
            return config if isinstance(config, dict) else {}
        except Exception as exc:
            log.error(
                f"Failed to load xcom providers: {exc}",
                source="XComConfigService",
            )
            return {}

    def get_provider(self, name: str) -> dict:
        try:
            config = self._load_providers()
            provider_name = "twilio" if name == "api" else name
            provider = config.get(provider_name) or {}

            # Explicitly fallback to environment vars for Twilio ("api")
            if provider_name == "twilio" and (not provider or not provider.get("account_sid")):
                def _env_first(keys):
                    if isinstance(keys, str):
                        return os.getenv(keys)
                    for key in keys or []:
                        if not key:
                            continue
                        value = os.getenv(key)
                        if value:
                            return value
                    return None

                provider = {
                    "enabled": True,
                    "account_sid": os.getenv("TWILIO_ACCOUNT_SID"),
                    "auth_token": os.getenv("TWILIO_AUTH_TOKEN"),
                    "flow_sid": _env_first(["TWILIO_FLOW_SID", "TWILIO_STUDIO_FLOW_SID"]),
                    "default_to_phone": _env_first(
                        ["MY_PHONE_NUMBER", "TWILIO_TO_PHONE", "TWILIO_DEFAULT_TO_PHONE"]
                    ),
                    "default_from_phone": _env_first(
                        ["TWILIO_PHONE_NUMBER", "TWILIO_FROM_PHONE", "TWILIO_DEFAULT_FROM_PHONE"]
                    ),
                    "use_studio": False,
                    "speak_plain": os.getenv("TWILIO_SPEAK_PLAIN"),
                }

            # Fallback to Twilio environment vars for SMS provider
            if provider_name == "sms" and (not provider or not provider.get("sid")):
                provider = {
                    "enabled": True,
                    "sid": os.getenv("TWILIO_ACCOUNT_SID"),
                    "token": os.getenv("TWILIO_AUTH_TOKEN"),
                    "from_number": os.getenv("TWILIO_FROM_PHONE") or os.getenv("TWILIO_PHONE_NUMBER"),
                    "default_recipient": os.getenv("TWILIO_TO_PHONE") or os.getenv("MY_PHONE_NUMBER"),
                    "carrier_gateway": os.getenv("SMS_CARRIER_GATEWAY"),
                }

            def apply_env(data: dict, mapping: dict) -> dict:
                for k, v in list(data.items()):
                    sub_map = mapping.get(k, {}) if isinstance(mapping, dict) else {}
                    if isinstance(v, dict):
                        data[k] = apply_env(v, sub_map if isinstance(sub_map, dict) else {})
                    else:
                        env_key = None
                        if isinstance(sub_map, str):
                            env_key = sub_map
                        elif isinstance(sub_map, (list, tuple)):
                            for cand in sub_map:
                                cand = str(cand or "")
                                if cand and os.getenv(cand):
                                    env_key = cand
                                    break
                        data[k] = _resolve_env(v, env_key)
                return data

            env_map = ENV_MAP.get(provider_name, {})
            if isinstance(provider, dict):
                provider = apply_env(deepcopy(provider), env_map)

            return provider
        except Exception as e:
            log.error(f"Failed to load provider config for '{name}': {e}", source="XComConfigService")
            return {}

    def channels_for(self, monitor: str) -> dict:
        """
        Build effective channel flags for the given monitor.
        LIVE/DRY-RUN comes from env only; 'voice' ignores global and defaults True.
        """

        cfg = self._load_providers() or {}
        g = cfg.get("global") or {}
        m = cfg.get(monitor) or {}
        live = os.getenv("SONIC_XCOM_LIVE", "1").strip().lower() in {"1", "true", "yes", "on"}
        return {
            "live": live,
            "system": bool(m.get("system", g.get("system", True))),
            "voice": bool(m.get("voice", True)),
            "sms": bool(m.get("sms", g.get("sms", False))),
            "tts": bool(m.get("tts", g.get("tts", False))),
        }
