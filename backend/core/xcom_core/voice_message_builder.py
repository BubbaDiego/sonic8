from __future__ import annotations

from typing import Any, Dict

from .voice_profiles import VoiceProfile
from .message_templates import build_liquidation_monitor_script


def _safe_num(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except Exception:
        return str(value)


def build_xcom_message(event: Dict[str, Any], profile: VoiceProfile) -> str:
    """
    Build a conservative spoken message for an XCom event.

    This is the single source of truth for Twilio voice + local TTS text.

    Canonical behavior for monitors:
      - liquid  → liquidation distance script (distance vs threshold)
      - profit  → profit in USD vs alert level
      - market  → percent move vs threshold
      - other   → generic "monitor in breach" text
    """

    mon = str(event.get("monitor", "") or "").lower()
    sym = str(event.get("symbol", "") or "")
    summary = str(
        event.get("summary")
        or event.get("short_text")
        or event.get("message")
        or ""
    ).strip()

    body_parts: list[str] = []

    # Optional profile prefix (e.g. "Sonic alert" or Polly-specific intro)
    if getattr(profile, "prefix", None):
        body_parts.append(profile.prefix.strip())

    # --- Monitor-specific logic -----------------------------------------------

    if mon == "liquid":
        # For liquidation, prefer the canonical script built from the event payload.
        # This ignores any ad-hoc "test" summary when we have distance + threshold
        # numbers available, so both voice and TTS share the same wording.
        liquid_text = build_liquidation_monitor_script(event)
        if liquid_text:
            body_parts.append(liquid_text)
        elif summary:
            # Fallback: if we couldn't extract numbers, use whatever summary was
            # attached to the event.
            body_parts.append(summary)
        else:
            # Last-resort legacy fallback (kept for safety)
            value = _safe_num(event.get("value_pct"))
            threshold = _safe_num(event.get("threshold_pct"))
            body_parts.append(
                f"Liquidation warning on {sym}. "
                f"Liq buffer {value} percent, threshold {threshold} percent."
            )

    else:
        # Non-liquidation monitors keep the existing precedence:
        #  1) summary/short_text/message if present
        #  2) monitor-specific fallbacks
        if summary:
            body_parts.append(summary)
        elif mon == "profit":
            pnl = _safe_num(event.get("pnl_usd"))
            thr = _safe_num(event.get("threshold_usd"))
            body_parts.append(
                f"Profit alert. P and L is {pnl} dollars, alert level {thr} dollars."
            )
        elif mon == "market":
            move = _safe_num(event.get("move_pct"))
            body_parts.append(
                f"Market move alert on {sym}. Price moved {move} percent."
            )
        else:
            body_parts.append(
                "Alert from Sonic. "
                f"Monitor {mon or 'unknown'} on {sym or 'portfolio'} is in breach."
            )

    # Optional profile suffix (e.g. “Goodbye.” or branding tag)
    if getattr(profile, "suffix", None):
        body_parts.append(profile.suffix.strip())

    return " ".join(part for part in body_parts if part)
