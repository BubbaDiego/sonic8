"""SMSService – send SMS via Twilio or fall back to email gateway."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.core.logging import log

# Optional Twilio import -------------------------------------------------
try:  # pragma: no cover
    from twilio.rest import Client
except ModuleNotFoundError:  # pragma: no cover
    Client = None

# Legacy email fallback --------------------------------------------------
from backend.core.xcom_core.email_service import EmailService


class SMSService:
    """Send SMS through Twilio with optional email fallback."""

    def __init__(self, cfg: dict):
        self.cfg = cfg or {}
        self._twilio_ok = (
            Client is not None
            and self.cfg.get("sid")
            and self.cfg.get("token")
            and self.cfg.get("from_number")
        )
        if not self._twilio_ok:
            log.warning(
                "Twilio SMS not fully configured – will fall back to email gateway",
                source="SMSService",
            )
            self._email_fallback = EmailService(cfg)

    # ------------------------------------------------------------------
    def send(self, to: str | None, body: str) -> bool:
        if not self.cfg.get("enabled", True):
            log.info("SMSService disabled in config", source="SMSService")
            return False

        to = to or self.cfg.get("default_recipient")
        if not to:
            log.error("No recipient provided to SMSService.send()", source="SMSService")
            return False

        # Twilio path -------------------------------------------------
        if self._twilio_ok:
            if self.cfg.get("dry_run"):
                log.debug(
                    f"\U0001f4ac [DRY-RUN] SMS to {to}: {body}",
                    source="SMSService",
                )
                return True
            try:
                client = Client(self.cfg["sid"], self.cfg["token"])
                msg = client.messages.create(
                    body=body,
                    from_=self.cfg["from_number"],
                    to=to,
                )
                log.success(f"\u2705 SMS sent (sid={msg.sid})", source="SMSService")
                return True
            except Exception as e:  # pragma: no cover
                log.error(f"\u274c Twilio SMS failed: {e}", source="SMSService")
                # fall through to email fallback if configured

        # Email-gateway fallback --------------------------------------
        gateway = self.cfg.get("carrier_gateway")
        if gateway:
            sms_email = f"{to}@{gateway}"
            return self._email_fallback.send(sms_email, "", body)

        return False
