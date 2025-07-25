# xcom/voice_service.py
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests  # noqa: F401  # retained for backward compatibility
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse

from backend.core.logging import log
try:
    from flask import current_app, has_app_context
except Exception:  # pragma: no cover - optional dependency
    current_app = type("obj", (), {})()

    def has_app_context():  # pragma: no cover - simple stub
        return False



class VoiceService:
    def __init__(self, config: dict):
        self.config = config

    def call(self, recipient: str, message: str) -> bool:
        """Initiate a Twilio voice call using ``message`` as spoken text.

        Errors are logged and the method returns ``False``. A death nail will
        only be triggered if ``suppress_death_on_error`` in the provider
        configuration is explicitly set to ``False``.
        """
        """  THIS MUST BE REMOVED """
        """ return False """

        if not self.config.get("enabled"):
            log.warning("Voice provider disabled", source="VoiceService")
            return False
        try:
            account_sid = self.config.get("account_sid") or os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = self.config.get("auth_token") or os.getenv("TWILIO_AUTH_TOKEN")
            from_phone = self.config.get("default_from_phone") or os.getenv("TWILIO_PHONE_NUMBER")
            to_phone = recipient or self.config.get("default_to_phone") or os.getenv("MY_PHONE_NUMBER")

            if not all([account_sid, auth_token, from_phone, to_phone]):
                log.error("Missing Twilio voice configuration", source="VoiceService")
                return False

            client = Client(account_sid, auth_token)
            vr = VoiceResponse()
            vr.say(message or "Hello from XCom.", voice="alice")

            call = client.calls.create(twiml=str(vr), to=to_phone, from_=from_phone)

            log.info(
                "🔍 Twilio Voice request debug",
                payload={"sid": call.sid, "to": to_phone, "from": from_phone},
                source="VoiceService",
            )

            return True

        except Exception as e:
            log.error(f"Voice call failed: {e}", source="VoiceService")
            if (
                not self.config.get("suppress_death_on_error", True)
                and os.getenv("DISABLE_DEATHNAIL_SERVICE", "0").lower()
                not in ("1", "true", "yes")
                and has_app_context()
                and hasattr(current_app, "system_core")
            ):
                # current_app.system_core.death(
                #     {
                #         "message": f"Twilio Voice Call failed: {e}",
                #         "payload": {
                #             "provider": "twilio",
                #             "to": to_phone,
                #             "from": from_phone,
                #         },
                #         "level": "HIGH",
                #     }
                # )
                log.info(
                    "🔈 Death nail suppressed for voice call failure",
                    source="VoiceService",
                )
            return False

