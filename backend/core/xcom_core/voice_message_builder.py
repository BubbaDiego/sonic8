from __future__ import annotations

from typing import Any, Dict

from .voice_profiles import VoiceProfile


def _safe_num(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except Exception:
        return str(value)


def build_xcom_message(event: Dict[str, Any], profile: VoiceProfile) -> str:
    """Build a conservative spoken message for an XCom event."""

    mon = str(event.get("monitor", "") or "")
    sym = str(event.get("symbol", "") or "")
    summary = str(
        event.get("summary")
        or event.get("short_text")
        or event.get("message")
        or ""
    ).strip()

    body_parts = []

    if profile.prefix:
        body_parts.append(profile.prefix.strip())

    if summary:
        body_parts.append(summary)
    else:
        if mon == "liquid":
            value = _safe_num(event.get("value_pct"))
            threshold = _safe_num(event.get("threshold_pct"))
            body_parts.append(
                f"Liquidation warning on {sym}. "
                f"Liq buffer {value} percent, threshold {threshold} percent."
            )
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

    if profile.suffix:
        body_parts.append(profile.suffix.strip())

    return " ".join(part for part in body_parts if part)
