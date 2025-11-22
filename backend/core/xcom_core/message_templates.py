from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

# Minimal symbol → human name mapping for nicer speech.
# Falls back to the raw symbol if not found.
_SYMBOL_NAME_MAP: Dict[str, str] = {
    "SOL": "Solana",
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
}


def _safe_num(value: Any) -> str:
    """Format a number for speech; fall back to str(value) on weird input."""
    try:
        return f"{float(value):.2f}"
    except Exception:
        return str(value)


def _fmt_number(value: Any) -> str:
    """Format a numeric field for speech with two decimal places."""
    return _safe_num(value)


def _normalize_symbol(sym: Any) -> str:
    """Normalize a symbol / asset field into an upper-case ticker."""
    if sym is None:
        return ""
    text = str(sym).strip()
    return text.upper()


def _asset_display_name(symbol: str) -> str:
    """
    Convert a ticker into a friendly spoken asset name.

    If we don't recognize the symbol, we just read the symbol itself.
    """
    sym = _normalize_symbol(symbol)
    if not sym:
        return "your position"
    return _SYMBOL_NAME_MAP.get(sym, sym)


def _extract_liquid_distances(event: Dict[str, Any]) -> Tuple[str | None, str | None, str]:
    """
    Extract (distance, threshold, symbol) for liquidation events.

    We support both:
      - value_pct / threshold_pct       (percent-based)
      - value + threshold.value         (raw distance units)

    Returns:
      (distance_text, threshold_text, symbol)
      where distance_text/threshold_text are already formatted via _safe_num,
      or (None, None, symbol) if we couldn't find enough data.
    """
    symbol = _normalize_symbol(
        event.get("symbol")
        or event.get("asset")
        or event.get("label")
        or ""
    )

    # 1) Percent-style fields, if present
    value_pct = event.get("value_pct")
    thr_pct = event.get("threshold_pct")
    if value_pct is not None and thr_pct is not None:
        return _safe_num(value_pct), _safe_num(thr_pct), symbol

    # 2) Generic numeric distance and threshold dict:
    #    value = current distance, threshold.value = alert level
    value = event.get("value")
    thr_val = None
    threshold = event.get("threshold")
    if isinstance(threshold, dict):
        thr_val = threshold.get("value")

    if value is not None and thr_val is not None:
        return _safe_num(value), _safe_num(thr_val), symbol

    # Anything else → not enough to build the canonical script.
    return None, None, symbol


def _extract_travel_pct(event: Dict[str, Any]) -> Optional[str]:
    """
    Try to extract a travel percent value for a position from an event.

    We support a few possible shapes:

      • event["travel_pct"]
      • event["travel_percent"]
      • event["meta"]["travel_pct"]
      • event["meta"]["travel_percent"]

    Returns a formatted string (e.g. "31.80%") or None if not found.
    """
    # direct fields on the event
    for key in ("travel_pct", "travel_percent", "travel"):
        if key in event and event.get(key) is not None:
            return _fmt_number(event.get(key)) + "%"

    # nested meta dict
    meta = event.get("meta")
    if isinstance(meta, dict):
        for key in ("travel_pct", "travel_percent", "travel"):
            if key in meta and meta.get(key) is not None:
                return _fmt_number(meta.get(key)) + "%"

    return None


def build_liquidation_monitor_script(event: Dict[str, Any]) -> str:
    """
    Build the canonical liquidation monitor script shared by voice + TTS.

    New wording (front-load important numbers):

        "A liquidation distance of <LD> violates a monitor threshold of <THR>.
         The current travel percent for this position is <TRAVEL>."

    If travel percent is not available, the second sentence is omitted.
    """
    dist_txt, thr_txt, symbol = _extract_liquid_distances(event)
    if dist_txt is None or thr_txt is None:
        # If we don't have enough data to speak the basics, bail out and let
        # the caller fall back to summary text.
        return ""

    asset_name = _asset_display_name(symbol)
    travel_txt = _extract_travel_pct(event)

    # First sentence: LD vs threshold
    # Example:
    #   "A liquidation distance of 1.62 violates a monitor threshold of 2.00."
    parts: list[str] = []
    parts.append(
        f"A liquidation distance of {dist_txt} violates a monitor threshold of {thr_txt}."
    )

    # Second sentence: travel percent, if available
    # Example:
    #   "The current travel percent for this position is 31.80%."
    if travel_txt:
        parts.append(
            f"The current travel percent for this position is {travel_txt}."
        )

    # Optional: keep a short asset tag at the end for clarity
    # Example:
    #   "Asset: Solana."
    if asset_name and asset_name not in ("the asset", "-"):
        parts.append(f"Asset: {asset_name}.")

    # Join sentences with spaces.
    return " ".join(parts)
