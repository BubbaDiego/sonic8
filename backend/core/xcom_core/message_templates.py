from __future__ import annotations

from typing import Any, Dict, Tuple

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


def build_liquidation_monitor_script(event: Dict[str, Any]) -> str:
    """
    Build the canonical liquidation monitor script shared by voice + TTS.

    Text shape (using formatted numbers and a normalized asset name):

        "Liquidation monitor alert. Current liquidation distance of <LD>
         is less than the alert level of <THR>. Time to mind <ASSET>. Goodbye."
    """
    dist_txt, thr_txt, symbol = _extract_liquid_distances(event)
    if dist_txt is None or thr_txt is None:
        return ""

    asset_name = _asset_display_name(symbol)

    return (
        "Liquidation monitor alert. "
        f"Current liquidation distance of {dist_txt} is less than the alert level of {thr_txt}. "
        f"Time to mind {asset_name}. Goodbye."
    )
