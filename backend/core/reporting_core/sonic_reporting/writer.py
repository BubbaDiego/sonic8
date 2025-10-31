# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional

from .writer import write_table  # ← no HAS_RICH import

# Indent to match Sync Data / Monitors
LEFT_PAD = "  "  # two spaces

# Asset icons (same set everywhere)
ICON_BTC = "🟡"
ICON_ETH = "🔷"
ICON_SOL = "🟣"
_ICON_MAP = {"BTC": ICON_BTC, "ETH": ICON_ETH, "SOL": ICON_SOL}

def _icon_for(sym: str) -> str:
    return _ICON_MAP.get(str(sym).upper(), "")

def _fmt_price(v: Any) -> str:
    try:
        if v is None or v == "":
            return "—"
        f = float(v)
        af = abs(f)
        if af >= 1000:
            s = f"{af/1000.0:.1f}".rstrip("0").rstrip(".") + "k"
            return s
        s = f"{f:.2f}".rstrip("0").rstrip(".")
        return s if s else "0"
    except Exception:
        return "—"

def _fmt_delta(cur: Any, prev: Any) -> str:
    try:
        if cur is None or prev is None:
            return "—"
        d = float(cur) - float(prev)
        s = f"{abs(d):.2f}".rstrip("0").rstrip(".")
        if s == "0": s = "0"
        return s if d >= 0 else f"−{s}"
    except Exception:
        return "—"

def _fmt_pct(cur: Any, prev: Any) -> str:
    try:
        if cur is None or prev is None or float(prev) == 0.0:
            return "—"
        p = (float(cur) - float(prev)) / float(prev) * 100.0
        s = f"{p:.2f}".rstrip("0").rstrip(".")
        if s == "0": s = "0"
        return f"{s}%"
    except Exception:
        return "—"

def _fmt_checked(rec: Dict[str, Any], now_ts: Optional[float]) -> str:
    try:
        if "age_s" in rec and isinstance(rec["age_s"], (int, float)):
            return f"({int(rec['age_s'])}s)"
        if "checked_s" in rec and isinstance(rec["checked_s"], (int, float)):
            return f"({int(rec['checked_s'])}s)"
        if "age" in rec and isinstance(rec["age"], (int, float)):
            return f"({int(rec['age'])}s)"
        if "checked_at" in rec and isinstance(rec["checked_at"], (int, float)) and isinstance(now_ts, (int, float)):
            return f"({max(0, int(now_ts - float(rec['checked_at'])))}s)"
    except Exception:
        pass
    return "(0s)"

def render(dl, prices: Any, now_ts: Optional[float] = None) -> None:
    """
    Prices table ONLY (no dashed title). Signature unchanged.
    """
    # Normalize to list of {"symbol":..., "current":..., "previous":...}
    recs: List[Dict[str, Any]] = []
    if isinstance(prices, dict):
        for sym, rec in prices.items():
            if isinstance(rec, dict):
                recs.append({"symbol": sym, **rec})
    elif isinstance(prices, list):
        for rec in prices:
            if isinstance(rec, dict) and "symbol" in rec:
                recs.append(rec)

    # Preferred order
    order = ["SOL", "ETH", "BTC"]
    seen = set()
    ordered: List[Dict[str, Any]] = []
    for s in order:
        for r in recs:
            if str(r.get("symbol", "")).upper() == s:
                ordered.append(r); seen.add(id(r))
    for r in sorted([x for x in recs if id(x) not in seen], key=lambda x: str(x.get("symbol","")).upper()):
        ordered.append(r)

    headers = [f"{LEFT_PAD}Asset", "Current", "Previous", "Δ", "A%", "Checked"]
    rows: List[List[str]] = []

    for r in ordered:
        sym = str(r.get("symbol", "")).upper()
        icon = _icon_for(sym)
        asset = f"{LEFT_PAD}{icon} {sym}" if icon else f"{LEFT_PAD}{sym}"
        cur   = r.get("current")
        prev  = r.get("previous")
        rows.append([
            asset,
            _fmt_price(cur),
            _fmt_price(prev) if prev is not None else "—",
            _fmt_delta(cur, prev),
            _fmt_pct(cur, prev),
            _fmt_checked(r, now_ts),
        ])

    if not rows:
        rows.append([f"{LEFT_PAD}—", "—", "—", "—", "—", "—"])

    write_table(title=None, headers=headers, rows=rows)
