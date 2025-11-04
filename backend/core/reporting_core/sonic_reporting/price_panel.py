# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Mapping, Tuple, Optional, Dict

ASSETS = ("BTC", "ETH", "SOL")

def _is_num(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False

def _sniff_price_map(obj: Any) -> Optional[Dict[str, float]]:
    """
    Return { 'BTC': float?, 'ETH': float?, 'SOL': float? } if obj looks like a price map.
    Values must be numeric; missing keys allowed.
    """
    if not isinstance(obj, Mapping):
        return None
    out: Dict[str, float] = {}
    seen = False
    for k in ASSETS:
        v = obj.get(k)
        if _is_num(v):
            out[k] = float(v)  # ok
            seen = True
    return out if seen else None

def _fmt_price(x: Optional[float]) -> str:
    if x is None:
        return "—"
    # Pretty short form like "107.4k" / "3.9k"
    absx = abs(x)
    if absx >= 1_000_000:
        return f"{x/1_000_000:.1f}m"
    if absx >= 1_000:
        return f"{x/1_000:.1f}k"
    return f"{x:.2f}"

def _fmt_delta(cur: Optional[float], prev: Optional[float]) -> Tuple[str, str]:
    if cur is None or prev is None:
        return ("—", "—")
    d = cur - prev
    pct = (d / prev * 100.0) if prev != 0 else 0.0
    sign = "" if d < 0 else "+"
    return (f"{sign}{d:.2f}", f"{sign}{pct:.2f}%")

def _extract_prices_and_ages(dl, csum) -> Tuple[Dict[str, float], Dict[str, float], str]:
    """
    Return (prices, prev_prices, source_tag).
    Ages are returned separately via csum['price_ages'] but not as prices.
    """
    # 1) csum hints first
    summary_prices = csum.get("prices")
    if isinstance(summary_prices, Mapping):
        cur_map: Dict[str, float] = {}
        prev_map: Dict[str, float] = {}
        for sym in ASSETS:
            info = summary_prices.get(sym)
            if isinstance(info, Mapping):
                cur = info.get("current")
                prev = info.get("previous")
                if _is_num(cur):
                    cur_map[sym] = float(cur)
                if _is_num(prev):
                    prev_map[sym] = float(prev)
        if cur_map or prev_map:
            return cur_map, prev_map, "csum.prices"
    for key in ("price_map", "last_prices"):
        m = _sniff_price_map(csum.get(key))
        if m:
            prev = _sniff_price_map(csum.get("prev_prices")) or {}
            return (m, prev, f"csum.{key}")

    # 2) dl.* common cache locations
    candidates = []
    for attr in ("cache", "portfolio", "positions", "system"):
        obj = getattr(dl, attr, None)
        if obj is None:
            continue
        # direct mapping
        m = _sniff_price_map(obj)
        if m:
            return (m, {}, f"dl.{attr}")
        # nested 'prices'
        m = _sniff_price_map(getattr(obj, "prices", None))
        if m:
            return (m, {}, f"dl.{attr}.prices")
        # nested 'last_prices'
        m = _sniff_price_map(getattr(obj, "last_prices", None))
        if m:
            return (m, {}, f"dl.{attr}.last_prices")
        candidates.append(f"dl.{attr}[no prices]")

    # 3) Nothing concrete
    # We keep returning empty dict (so renderer prints blanks) and show attempted paths.
    return ({}, {}, "none(" + ", ".join(candidates) + ")")

def render(dl, csum, default_json_path=None):
    write_line = print  # sequencer injects same convention

    prices, prev, src = _extract_prices_and_ages(dl, csum)
    ages = csum.get("price_ages") or csum.get("price_age") or {}

    write_line(" 💰 Prices")
    write_line("")
    write_line(" Asset       Current   Previous   Δ   Δ%   Checked")
    write_line("")
    # Debug source tag
    write_line(f"[PRICE] source: {src}")
    write_line("")

    if not prices and not prev:
        # still render skeleton
        for a in ASSETS:
            write_line(f" {symbol_emoji(a)} {a:<9}  —           —          —   —     (—)")
        write_line("")
        return True

    for a in ASSETS:
        cur = prices.get(a)
        prv = prev.get(a)
        d, pct = _fmt_delta(cur, prv)
        checked = "—"
        try:
            age = ages.get(a)
            if _is_num(age):
                # render like "0s", "12s", "3m", "5m+"
                s = float(age)
                checked = f"{int(s)}s" if s < 60 else f"{int(s//60)}m"
        except Exception:
            pass

        write_line(
            f" {symbol_emoji(a)} {a:<9} "
            f"{_fmt_price(cur):>8}    {_fmt_price(prv):>8}   {d:>6}  {pct:>6}   ({checked})"
        )
    write_line("")
    return True

def symbol_emoji(asset: str) -> str:
    a = (asset or "").upper()
    return {"BTC": "🟡", "ETH": "🔷", "SOL": "🟣"}.get(a, "•")
