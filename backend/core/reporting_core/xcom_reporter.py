from __future__ import annotations

import re
from typing import Optional, Tuple

from backend.core.reporting_core.task_events import phase_start, phase_end

# Phase keys (use blue-phase lines)
#   xcom_voice  → ☎️ Twilio Voice
#   xcom_sms    → 📨 Twilio SMS
#   xcom_tts    → 🔊 TTS
#   xcom_sound  → 🔔 System Sound

_ERR_HINTS = {
    # Auth / credentials
    "20003": "Auth failed: check SID/AUTH_TOKEN (project creds) and region.",
    # Phone numbers
    "21211": "Invalid 'To' number format.",
    "21606": "'From' is not a valid outbound caller ID for this account.",
    "21608": "Trial account: 'To' number must be verified.",
    # Permissions / geo
    "13227": "Call blocked by geo permissions / Voice Geographic Permissions.",
    "14107": "Call blocked by geo permissions.",
    # Webhook / media
    "11200": "HTTP retrieval failure (TwiML URL or webhook error).",
}


def _mask(v: Optional[str]) -> str:
    if not v or v == "-":
        return "–"
    return f"{v[:3]}…"


def _parse_twilio_error(exc: Exception) -> Tuple[Optional[str], str]:
    """Returns (code, message). Tries to read attributes then falls back to regex."""

    code: Optional[str] = None
    msg = str(exc).strip()
    # Try attribute first
    try:
        code_attr = getattr(exc, "code", None)
        if code_attr:
            code = str(code_attr)
    except Exception:
        pass
    # Fallback: extract .../errors/<code>
    if not code:
        match = re.search(r"/errors/(\d+)", msg)
        if match:
            code = match.group(1)
    # Clean message a bit
    msg = re.sub(r"\s+", " ", msg)
    return code, msg


def twilio_start(channel: str, to: str, from_: str) -> None:
    to_mask = _mask(str(to) if to is not None else "")
    from_mask = _mask(str(from_) if from_ is not None else "")
    label = f"Twilio {channel} → to={to_mask} • from={from_mask}"
    phase_start(f"xcom_{channel}", label)


def twilio_success(channel: str, note: str = "") -> None:
    phase_end(f"xcom_{channel}", "ok", note=(note or "ok"))


def twilio_fail(channel: str, exc: Exception) -> None:
    code, message = _parse_twilio_error(exc)
    hint = _ERR_HINTS.get(code or "", "")
    note = f"{(code + ' — ') if code else ''}{message}"
    if hint:
        note += f"  ({hint})"
    phase_end(f"xcom_{channel}", "fail", note=note)
