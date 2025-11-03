# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Mapping, List, Dict, Tuple, Optional

def _as_dict(row: Any) -> Mapping[str, Any]:
    if isinstance(row, Mapping):
        return row
    return getattr(row, "__dict__", {}) or {}

def _get(row: Mapping[str, Any], *names: str) -> Any:
    for n in names:
        if n in row:
            return row.get(n)
    # nested common spots
    for nest in ("risk", "meta", "stats"):
        d = row.get(nest)
        if isinstance(d, Mapping):
            for n in names:
                if n in d:
                    return d.get(n)
    return None

def _is_num(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False

def _fmt_money(x: Optional[float]) -> str:
    if x is None:
        return "—"
    sgn = "-" if x < 0 else ""
    v = abs(float(x))
    if v >= 1_000_000:
        return f"{sgn}${v/1_000_000:.1f}m"
    if v >= 1_000:
        return f"{sgn}${v/1_000:.1f}k"
    return f"{sgn}${v:.2f}"

def _fmt_x(x: Optional[float]) -> str:
    if x is None:
        return "—"
    return f"{float(x):.2f}×"

def _fmt_pct(x: Optional[float]) -> str:
    if x is None:
        return "—"
    return f"{float(x):.2f}%"

def _sym(row: Mapping[str, Any]) -> Optional[str]:
    v = _get(row, "asset", "symbol", "coin", "ticker")
    if isinstance(v, str) and v:
        return v.upper()
    return None

def _side(row: Mapping[str, Any]) -> str:
    v = str(_get(row, "side", "position", "dir", "direction") or "").lower()
    if v.startswith("l"):
        return "LONG"
    if v.startswith("s"):
        return "SHORT"
    return "-"

def _value(row: Mapping[str, Any]) -> Optional[float]:
    for k in ("value_usd", "value", "notional", "size_usd"):
        v = _get(row, k)
        if _is_num(v):
            return float(v)
    return None

def _pnl(row: Mapping[str, Any]) -> Optional[float]:
    for k in ("pnl_usd", "pnl", "profit_usd", "profit"):
        v = _get(row, k)
        if _is_num(v):
            return float(v)
    return None

def _lev(row: Mapping[str, Any]) -> Optional[float]:
    for k in ("lev", "leverage"):
        v = _get(row, k)
        if _is_num(v):
            return float(v)
    return None

def _liq(row: Mapping[str, Any]) -> Optional[float]:
    for k in ("liq", "liq_dist", "liquidation", "liquidation_distance", "liq_pct"):
        v = _get(row, k)
        if _is_num(v):
            return float(v)
    return None

def _travel(row: Mapping[str, Any]) -> Optional[float]:
    for k in ("travel", "travel_pct"):
        v = _get(row, k)
        if _is_num(v):
            return float(v)
    return None

def _collect_positions(dl, csum) -> Tuple[List[Mapping[str, Any]], str, List[str]]:
    """
    Try multiple sources; return (rows, source_tag, attempts).
    """
    attempts: List[str] = []

    # 1) Summary injection
    for key in ("positions", "pos_rows", "positions_table"):
        v = csum.get(key)
        if isinstance(v, list) and v:
            return ([ _as_dict(r) for r in v ], f"csum.{key}", attempts)

    # 2) Common dl.* paths
    for root in ("positions", "cache", "portfolio"):
        robj = getattr(dl, root, None)
        if robj is None:
            attempts.append(f"dl.{root}: None")
            continue

        # direct list
        if isinstance(robj, list) and robj:
            return ([ _as_dict(r) for r in robj ], f"dl.{root}", attempts)

        # attributes likely to hold lists
        for attr in ("active", "active_positions", "positions", "last_positions", "snapshot"):
            got = getattr(robj, attr, None)
            if isinstance(got, list) and got:
                return ([ _as_dict(r) for r in got ], f"dl.{root}.{attr}", attempts)
            # callable getter
            meth = getattr(robj, attr, None)
            if callable(meth):
                try:
                    v = meth()
                    if isinstance(v, list) and v:
                        return ([ _as_dict(r) for r in v ], f"dl.{root}.{attr}()", attempts)
                except Exception:
                    pass
            attempts.append(f"dl.{root}.{attr}: empty")

    # 3) Nothing
    return ([], "none", attempts)

def _emoji(asset: str) -> str:
    a = (asset or "").upper()
    return {"BTC": "🟡", "ETH": "🔷", "SOL": "🟣"}.get(a, "•")

def render(dl, csum) -> bool:
    write_line = print

    rows, src, attempts = _collect_positions(dl, csum)

    write_line("  ---------------------- 📈  Positions  ----------------------")
    write_line(" Asset   Side        Value        PnL     Lev      Liq   Travel")

    if not rows:
        write_line(" -      -             -           -       -        -        -")
        write_line("                       $0.00     $0.00       -                 -")
        write_line("")
        write_line(f"[POSITIONS] source: {src}")
        if attempts:
            write_line("[POSITIONS] attempts: " + "; ".join(attempts[:6]))
        write_line("")
        return True

    tot_value = 0.0
    tot_pnl = 0.0
    for r in rows:
        a = _sym(r) or "-"
        s = _side(r)
        v = _value(r); p = _pnl(r); l = _lev(r); q = _liq(r); t = _travel(r)
        if v is not None: tot_value += v
        if p is not None: tot_pnl += p

        write_line(
            f" {_emoji(a)} {a:<4}  {s:<6}  "
            f"{_fmt_money(v):>10}  {_fmt_money(p):>8}  "
            f"{_fmt_x(l):>6}  {('%.2f' % q) if q is not None else '—':>6}  "
            f"{_fmt_pct(t):>7}"
        )

    write_line(f"                       {_fmt_money(tot_value):>10}  {_fmt_money(tot_pnl):>8}       -                 -")
    write_line("")
    write_line(f"[POSITIONS] source: {src}")
    write_line("")
    return True
