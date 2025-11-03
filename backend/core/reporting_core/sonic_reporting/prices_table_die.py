# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any, List, Tuple
from .writer import write_table, HAS_RICH

ICON_BY_ASSET = {"BTC": "🟡", "ETH": "🔷", "SOL": "🟣"}

# ANSI color for column headers (bright cyan)
HDR = "\x1b[96m"
RST = "\x1b[0m"


def _abbr(n):
    try:
        v = float(n)
    except Exception:
        return "—"
    if abs(v) >= 1_000_000_000: return f"{v/1_000_000_000:.1f}B"
    if abs(v) >= 1_000_000:     return f"{v/1_000_000:.1f}M"
    if abs(v) >= 1_000:         return f"{v/1_000:.1f}k"
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s

def _delta(curr, prev):
    try:
        c = float(curr); p = float(prev) if prev is not None else None
        if p is None: return "—", "—"
        d = c - p
        pct = (d / p) * 100 if p != 0 else 0.0
        ds = f"{d:+.2f}".rstrip("0").rstrip(".")
        ps = f"{pct:+.2f}%".rstrip("0").rstrip(".")
        return ds, ps
    except Exception:
        return "—", "—"

def _age(a):
    if a is None or a == "": return "(—)"
    try:
        sec = float(a)
        if sec < 1: return "(0s)"
        if sec < 60: return f"({int(sec)}s)"
        return f"({int(sec//60)}m)"
    except Exception:
        return f"({a})"

def _top3(csum: Dict[str, Any]) -> List[Tuple[str, float]]:
    raw = csum.get("prices_top3") or []
    out = []
    for it in raw:
        if isinstance(it, (list, tuple)) and len(it) >= 2:
            out.append((str(it[0]).upper(), it[1]))
        elif isinstance(it, dict):
            sym = (it.get("asset") or it.get("symbol") or it.get("market") or "?").upper()
            price = it.get("price") or it.get("current_price")
            out.append((sym, price))
    return out

def render(csum: Dict[str, Any]) -> None:
    """
    Render the prices table WITHOUT an internal title.
    The dashed header ("---------------------- 💰  Prices  ----------------------")
    is printed by the sequencer.
    """
    headers = ["Asset", "Current", "Previous", "Δ", "A%", "Checked"]
    render_headers = [f"{HDR}{h}{RST}" for h in headers] if not HAS_RICH else headers

    current = _top3(csum)
    prev_map = csum.get("prices_prev") or {}   # e.g., {"BTC": 110500, ...}
    ages = csum.get("price_ages") or {}

    rows: List[List[str]] = []
    for sym, price in current:
        curr = _abbr(price)
        prev_raw = prev_map.get(sym)
        prev = _abbr(prev_raw) if prev_raw is not None else "—"
        d, dp = _delta(price, prev_raw)
        icon = ICON_BY_ASSET.get(sym, "◻️")
        rows.append([f"{icon} {sym}", curr, prev, d, dp, _age(ages.get(sym))])

    if not rows:
        for sym in ("BTC", "ETH", "SOL"):
            icon = ICON_BY_ASSET.get(sym, "◻️")
            rows.append([f"{icon} {sym}", "—", "—", "—", "—", "(—)"])

    # No title row → pass None so only headers + rows render.
    write_table(None, render_headers, rows)
