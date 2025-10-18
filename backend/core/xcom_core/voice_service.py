"""Twilio voice calling utilities for XCom notifications."""

from __future__ import annotations

import logging
import os
import re
from typing import Optional, Tuple, TYPE_CHECKING

from twilio.rest import Client

from backend.core.reporting_core.xcom_reporter import (
    twilio_fail,
    twilio_skip,
    twilio_start,
    twilio_success,
)
from backend.core.config_core import sonic_config_bridge as C

if TYPE_CHECKING:  # pragma: no cover - typing only
    from backend.core.xcom_core.xcom_config_service import XComConfigService

E164 = re.compile(r"^\+[1-9]\d{6,14}$")


def _xcom_live() -> bool:
    """Return the XCom live/dry-run toggle from JSON config."""
    return C.get_xcom_live()


def _as_bool(value):
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


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
        self,
        to_number: Optional[str],
        subject: str,
        body: str,
        *,
        monitor_name: str | None = None,
        xcom_config_service: "XComConfigService" | None = None,
        channels: Optional[dict] = None,
    ) -> Tuple[bool, str, str, str]:
        """Initiate a voice notification via Twilio.

        Returns a tuple of ``(success, sid_or_error, to_number, from_number)``. When
        a Studio Flow SID is configured we prefer that, otherwise a simple TwiML
        call is used.
        """

        if not self.config.get("enabled", False):
            self.logger.warning("VoiceService: provider disabled → skipping call")
            return False, "provider-disabled", "", ""

        effective_channels = channels
        if effective_channels is None and monitor_name and xcom_config_service:
            try:
                effective_channels = xcom_config_service.channels_for(monitor_name)
            except Exception:
                effective_channels = None

        if effective_channels is not None:
            live = bool(effective_channels.get("live", True))
            voice_enabled = bool(effective_channels.get("voice", True))
        else:
            live = _xcom_live()
            voice_enabled = True

        if not live or not voice_enabled:
            self.logger.warning("VoiceService: provider disabled -> skipping call")
            return False, "disabled", "", ""

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
        use_studio = _as_bool(self.config.get("use_studio", False))

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

        voice_name = (self.config.get("voice_name") or "Polly.Amy").strip()
        if not voice_name:
            voice_name = "Polly.Amy"

        try:
            if not live:
                twilio_skip("voice", "disabled")
                return False, "xcom-disabled", to_resolved, from_number
            if use_studio and flow_sid and not re.search(r"your_flow_sid_here", flow_sid, re.IGNORECASE):
                execution = self.client.studio.v2.flows(flow_sid).executions.create(
                    to=to_resolved,
                    from_=from_number,
                    parameters={
                        "subject": subject or "Sonic Alert",
                        "body": body or "",
                        "voice": voice_name,
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

            # If speak_plain is enabled, say exactly the body (or subject); otherwise keep a small prefix
            speak_plain = _as_bool(self.config.get("speak_plain", False))

            # Tunables (ms) — small intro/outro cushions to avoid clip at start/end
            start_delay_ms = int(self.config.get("start_delay_ms", 400))  # 0.4s before speaking
            end_delay_ms = int(self.config.get("end_delay_ms", 250))  # 0.25s after speaking
            # Smooth pace (percentage of normal). 90–98 feels natural for most messages.
            prosody_rate_pct = int(self.config.get("prosody_rate_pct", 94))

            text = (body or subject or "")
            if not text:
                text = "Alert"
            if not speak_plain:
                text = f"Sonic says: {text}"

            # Basic escaping to keep TwiML/SSML safe
            def _esc(s: str) -> str:
                return s.replace("&", "and").replace("<", " ").replace(">", " ")

            # If we’re on a Polly voice, leverage SSML <break/> and <prosody>.
            # Otherwise, fall back to a TwiML <Pause/> prefix to create the intro cushion.
            is_polly = voice_name.lower().startswith("polly.")
            if is_polly:
                ssml = (
                    f"<prosody rate='{prosody_rate_pct}%'>"
                    f"<break time='{start_delay_ms}ms'/>"
                    f"{_esc(text)}"
                    f"<break time='{end_delay_ms}ms'/>"
                    f"</prosody>"
                )
                twiml = f"<Response><Say voice='{voice_name}'>{ssml}</Say></Response>"
            else:
                # TwiML-level pause first, then speak (no SSML available for non-Polly voices)
                pause_secs = max(0, round(start_delay_ms / 1000, 1))
                twiml = (
                    f"<Response>"
                    f"<Pause length='{pause_secs}'/>"
                    f"<Say voice='{voice_name}'>{_esc(text)}</Say>"
                    f"</Response>"
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
