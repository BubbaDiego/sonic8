# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Any
from .writer import write_line
from .styles import ICON_PRICE

def _abbr(n):
    try:
        v = float(n)
    except Exception:
        return str(n)
    if abs(v) >= 1_000_000_000: return f"{v/1_000_000_000:.1f}B"
    if abs(v) >= 1_000_000:     return f"{v/1_000_000:.1f}M"
    if abs(v) >= 1_000:         return f"{v/1_000:.1f}k"
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s

def _age(a):
    if a is None or a == "": return "(—)"
    try:
        sec = float(a)
        if sec < 1: return "(0s)"
        if sec < 60: return f"({int(sec)}s)"
        return f"({int(sec//60)}m)"
    except Exception:
        return f"({a})"

def render(csum: Dict[str, Any]) -> None:
    pt = csum.get("prices_top3") or []
    ages = csum.get("price_ages") or {}
    parts = []
    for item in pt:
        if isinstance(item, (list,tuple)) and len(item) >= 2:
            sym, price = item[0], item[1]
        elif isinstance(item, dict):
            sym, price = (item.get("asset") or item.get("symbol") or item.get("market") or "?"), item.get("price") or item.get("current_price")
        else:
            continue
        parts.append(f"{sym} {_abbr(price)} {_age(ages.get(str(sym))) }")
    write_line(f"{ICON_PRICE} Prices   : " + " • ".join(parts))
