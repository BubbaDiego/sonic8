"""Twilio voice calling utilities for XCom notifications."""

from __future__ import annotations

import logging
import os
import re
from typing import Optional, Tuple

from twilio.rest import Client

from backend.core.reporting_core.xcom_reporter import (
    twilio_fail,
    twilio_skip,
    twilio_start,
    twilio_success,
)

E164 = re.compile(r"^\+[1-9]\d{6,14}$")


def _xcom_live() -> bool:
    return os.getenv("SONIC_XCOM_LIVE", "1").strip().lower() not in {"0", "false", "no", "off"}


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

    def _normalize_e164(self, raw: str, default_country: str = "+1") -> str:
        """Best-effort cleanup of common North American number formats."""

        number = str(raw or "").strip()
        if E164.match(number):
            return number

        digits = re.sub(r"\D", "", number)
        if len(digits) == 10:
            return f"{default_country}{digits}"
        if len(digits) == 11 and digits.startswith("1"):
            return f"+{digits}"
        if number.startswith("+6") and digits.startswith("619") and len(digits) == 10:
            return f"{default_country}{digits}"

        return number

    def _validate_e164(self, label: str, number: str) -> str:
        if not number or not E164.match(number):
            raise ValueError(f"{label} must be E.164 like +14155552671 (got {number!r})")
        return number

    def call(
        self, to_number: Optional[str], subject: str, body: str
    ) -> Tuple[bool, str, str, str]:
        """Initiate a voice notification via Twilio.

        Returns a tuple of ``(success, sid_or_error, to_number, from_number)``. When
        a Studio Flow SID is configured we prefer that, otherwise a simple TwiML
        call is used.
        """

        if not self.config.get("enabled", False):
            self.logger.warning("VoiceService: provider disabled → skipping call")
            return False, "provider-disabled", "", ""

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
        use_studio = bool(self.config.get("use_studio", False))

        raw_from, raw_to = from_number, to_resolved
        from_number = self._normalize_e164(from_number)
        to_resolved = self._normalize_e164(to_resolved)
        self.logger.info(
            "VoiceService: dialing (to=%s → %s, from=%s → %s)",
            raw_to,
            to_resolved,
            raw_from,
            from_number,
        )

        from_number = self._validate_e164("TWILIO_FROM_PHONE", from_number)
        to_resolved = self._validate_e164("Recipient", to_resolved)

        twilio_start("voice")

        try:
            if not _xcom_live():
                twilio_skip("voice", "disabled")
                return False, "xcom-disabled", to_resolved, from_number
            if use_studio and flow_sid and not re.search(r"your_flow_sid_here", flow_sid, re.IGNORECASE):
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
                twilio_success("voice", note="studio execution")
                return True, sid, to_resolved, from_number

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
            twilio_success("voice", note="call created")
            return True, sid, to_resolved, from_number
        except Exception as exc:  # pragma: no cover - Twilio network errors
            # Let the reporter surface the concise failure; avoid duplicate logging here.
            twilio_fail("voice", exc)
            # Do not re-raise; the failure is reported upstream and we return a tuple.
            return False, str(exc), to_resolved, from_number
