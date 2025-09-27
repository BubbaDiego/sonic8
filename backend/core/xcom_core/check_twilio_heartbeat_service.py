import os
from typing import Dict

try:
    from flask import current_app, has_app_context
except Exception:  # pragma: no cover - optional dependency
    current_app = type("obj", (), {})()

    def has_app_context():  # pragma: no cover - simple stub
        return False
from twilio.rest import Client

from backend.core.logging import log
from backend.core.xcom_core.voice_service import VoiceService


class CheckTwilioHeartbeatService:
    """Verify Twilio credentials and optionally place a test voice call."""

    def __init__(self, config: Dict):
        self.config = config or {}

    def _load_creds(self):
        account_sid = self.config.get("account_sid") or os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = self.config.get("auth_token") or os.getenv("TWILIO_AUTH_TOKEN")
        from_phone = self.config.get("default_from_phone") or os.getenv("TWILIO_PHONE_NUMBER")
        to_phone = self.config.get("default_to_phone") or os.getenv("MY_PHONE_NUMBER")
        return account_sid, auth_token, from_phone, to_phone

    def check(self, dry_run: bool = True) -> Dict:
        """Return dict with success status and whether a call was placed."""
        result = {"success": False, "call_placed": False}
        account_sid, auth_token, from_phone, to_phone = self._load_creds()
        try:
            if not account_sid or not auth_token:
                raise Exception("Missing Twilio credentials")

            client = Client(account_sid, auth_token)
            client.api.accounts(account_sid).fetch()

            if not dry_run:
                if not from_phone or not to_phone:
                    raise Exception("Missing from/to phone numbers")
                ok, sid = VoiceService(self.config).call(
                    to_phone,
                    "XCom Heartbeat",
                    "XCom heartbeat check",
                )
                if not ok:
                    raise Exception(f"Voice call failed: {sid or 'unknown error'}")
                result["call_placed"] = True
                if sid:
                    result["twilio_sid"] = sid

            result["success"] = True
        except Exception as exc:
            log.error(f"Twilio heartbeat failed: {exc}", source="CheckTwilioHeartbeatService")
            if has_app_context() and hasattr(current_app, "system_core"):
                # current_app.system_core.death(
                #     {
                #         "message": f"Twilio heartbeat failure: {exc}",
                #         "payload": {"provider": "twilio"},
                #         "level": "HIGH",
                #     }
                # )
                log.info(
                    "🔈 Death nail suppressed for Twilio heartbeat failure",
                    source="CheckTwilioHeartbeatService",
                )
            result["error"] = str(exc)
        return result
