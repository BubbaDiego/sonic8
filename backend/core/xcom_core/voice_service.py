"""Twilio voice calling utilities for XCom notifications."""

from __future__ import annotations

import logging
import os
import re
from typing import Optional, Tuple

from twilio.rest import Client

E164 = re.compile(r"^\+[1-9]\d{6,14}$")


class VoiceService:
    """Thin wrapper around the Twilio SDK with Studio Flow support."""

    def __init__(self, config: dict | None):
        self.config = config or {}
        self.logger = logging.getLogger("xcom.voice")

        account_sid = self.config.get("account_sid") or os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = self.config.get("auth_token") or os.getenv("TWILIO_AUTH_TOKEN")
        if not account_sid or not auth_token:
            raise RuntimeError("Twilio creds missing (ACCOUNT_SID / AUTH_TOKEN).")

        self.client = Client(account_sid, auth_token)

    @staticmethod
    def _pick(*values: Optional[str]) -> str:
        for value in values:
            if value is not None and str(value).strip():
                return str(value).strip()
        return ""

    def _validate_e164(self, label: str, number: str) -> str:
        if not number or not E164.match(number):
            raise ValueError(f"{label} must be E.164 like +14155552671 (got {number!r})")
        return number

    def call(self, to_number: Optional[str], subject: str, body: str) -> Tuple[bool, str]:
        """Initiate a voice notification via Twilio.

        Returns a tuple of ``(success, sid_or_error)``. When a Studio Flow SID is
        configured we prefer that, otherwise a simple TwiML call is used.
        """

        if not self.config.get("enabled", False):
            self.logger.warning("VoiceService: provider disabled → skipping call")
            return False, "provider-disabled"

        from_number = self._pick(
            self.config.get("default_from_phone"),
            os.getenv("TWILIO_FROM_PHONE"),
            os.getenv("TWILIO_PHONE_NUMBER"),
        )
        to_resolved = self._pick(
            to_number,
            self.config.get("default_to_phone"),
            os.getenv("TWILIO_TO_PHONE"),
            os.getenv("MY_PHONE_NUMBER"),
        )
        flow_sid = self._pick(self.config.get("flow_sid"), os.getenv("TWILIO_FLOW_SID"))

        from_number = self._validate_e164("TWILIO_FROM_PHONE", from_number)
        to_resolved = self._validate_e164("Recipient", to_resolved)

        try:
            if flow_sid and not re.search(r"your_flow_sid_here", flow_sid, re.IGNORECASE):
                execution = self.client.studio.v2.flows(flow_sid).executions.create(
                    to=to_resolved,
                    from_=from_number,
                    parameters={
                        "subject": subject or "Sonic Alert",
                        "body": body or "",
                    },
                )
                sid = getattr(execution, "sid", "")
                self.logger.info(
                    "Twilio Studio execution created: sid=%s to=%s from=%s flow=%s",
                    sid,
                    to_resolved,
                    from_number,
                    flow_sid,
                )
                return True, sid

            twiml = (
                "<Response><Say voice='Polly.Matthew'>Sonic says: "
                f"{body or subject or 'Alert'}</Say></Response>"
            )
            call = self.client.calls.create(to=to_resolved, from_=from_number, twiml=twiml)
            sid = getattr(call, "sid", "")
            self.logger.info(
                "Twilio call created: sid=%s to=%s from=%s",
                sid,
                to_resolved,
                from_number,
            )
            return True, sid
        except Exception as exc:  # pragma: no cover - Twilio network errors
            self.logger.exception("Twilio voice call failed: %s", exc)
            return False, str(exc)
