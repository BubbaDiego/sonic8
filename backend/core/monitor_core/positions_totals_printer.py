from __future__ import annotations
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Minimal ANSI styling; safe if your console supports it. Set to "" to disable.
BOLD = "\x1b[1m"
LINE_COLOR = "\x1b[38;5;45m"  # cyan-ish
RESET = "\x1b[0m"

def _as_float(x: Any) -> Optional[float]:
    """Coerce numbers/strings like '$1,234.56', '12.3%', '10.5x', '9.90×' to float."""
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        for ch in ("$", ",", "%", "x", "X", "×"):
            s = s.replace(ch, "")
        s = s.replace("\u2013", "-")  # en-dash
        try:
            return float(s)
        except Exception:
            import re
            m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
            if m:
                try:
                    return float(m.group(0))
                except Exception:
                    return None
    return None

def _w(width_map: Dict[str, int], *keys: str, default: int = 0) -> int:
    """Width helper allowing synonyms, e.g., ('sz','size') → width."""
    for k in keys:
        if k in width_map:
            return int(width_map[k])
    return default

def _extract_fields(row: Any) -> Dict[str, Optional[float]]:
    """
    Accept:
      - dict-like with keys (case-insensitive): value, pnl, size, lev, travel
      - sequence with 7 or 8 columns:
          7-col: [Asset, Side, Value, PnL, Lev, Liq, Travel]
          8-col: [Asset, Side, Value, PnL, Size, Lev, Liq, Travel]
    """
    if isinstance(row, dict):
        def get(d: Dict[str, Any], name: str) -> Any:
            ln = name.lower()
            for k, v in d.items():
                if isinstance(k, str) and k.lower() == ln:
                    return v
            return None
        size = (_as_float(get(row, "size"))
                or _as_float(get(row, "qty"))
                or _as_float(get(row, "amount"))
                or _as_float(get(row, "position_size")))
        return {
            "value":  _as_float(get(row, "value")),
            "pnl":    _as_float(get(row, "pnl")),
            "size":   size,
            "lev":    _as_float(get(row, "lev")),
            "travel": _as_float(get(row, "travel")),
        }

    if isinstance(row, Sequence):
        # 8 columns (preferred: includes Size)
        if len(row) >= 8:
            return {
                "value":  _as_float(row[2]),
                "pnl":    _as_float(row[3]),
                "size":   _as_float(row[4]),
                "lev":    _as_float(row[5]),
                "travel": _as_float(row[7]),
            }
        # 7 columns (no Size)
        if len(row) >= 7:
            return {
                "value":  _as_float(row[2]),
                "pnl":    _as_float(row[3]),
                "size":   None,
                "lev":    _as_float(row[4]),
                "travel": _as_float(row[6]),
            }

    return {"value": None, "pnl": None, "size": None, "lev": None, "travel": None}

def compute_weighted_totals(rows: List[Any]) -> Dict[str, Optional[float]]:
    """
    Compute ΣValue, ΣPnL, and Size-weighted averages for Lev/Travel.
    If Size is missing for a row, weight that row by |Value| so the footer never collapses.
    """
    total_value = 0.0
    total_pnl = 0.0
    w_lev_num = w_lev_den = 0.0
    w_trv_num = w_trv_den = 0.0

    for r in rows:
        f = _extract_fields(r)
        v, p, s, l, t = f["value"], f["pnl"], f["size"], f["lev"], f["travel"]

        if v is not None:
            total_value += v
        if p is not None:
            total_pnl += p

        weight = abs(s) if s is not None else (abs(v) if v is not None else None)
        if weight is not None:
            if l is not None:
                w_lev_num += weight * l
                w_lev_den += weight
            if t is not None:
                w_trv_num += weight * t
                w_trv_den += weight

    lev_w = (w_lev_num / w_lev_den) if w_lev_den > 0 else None
    trv_w = (w_trv_num / w_trv_den) if w_trv_den > 0 else None

    return {
        "value": total_value,
        "pnl": total_pnl,
        "avg_lev_weighted": lev_w,
        "avg_travel_weighted": trv_w,
    }

def _fmt_money(v: Optional[float]) -> str:
    return f"${v:,.2f}" if isinstance(v, float) else "-"

def _fmt_lev(v: Optional[float]) -> str:
    return f"{v:.2f}×" if isinstance(v, float) else "-"

def _fmt_pct(v: Optional[float]) -> str:
    return f"{v:.2f}%" if isinstance(v, float) else "-"

def print_positions_totals_line(
    totals: Dict[str, Optional[float]],
    width_map: Dict[str, int],
    color: str = LINE_COLOR,
    bold: bool = BOLD,
) -> None:
    """
    Print ONE aligned totals line directly under the last Positions row.
    Supports 7 or 8 columns (presence of Size column inferred from width_map).
    Accepts short keys ('a','s','v','p','sz','l','liq','t') and long keys
    ('asset','side','value','pnl','size','lev','liq','travel').
    """
    has_size = (("sz" in width_map) or ("size" in width_map))

    a  = _w(width_map, "a",    "asset")
    s  = _w(width_map, "s",    "side")
    v  = _w(width_map, "v",    "value")
    p  = _w(width_map, "p",    "pnl")
    sz = _w(width_map, "sz",   "size")
    l  = _w(width_map, "l",    "lev")
    lq = _w(width_map, "liq",  "liquidation", "liquid", "liqd")
    t  = _w(width_map, "t",    "travel")

    val = _fmt_money(totals.get("value"))
    pnl = _fmt_money(totals.get("pnl"))
    lev = _fmt_lev(totals.get("avg_lev_weighted"))
    trv = _fmt_pct(totals.get("avg_travel_weighted"))

    if has_size:
        line = (
            f"{'':<{a}} "
            f"{'':<{s}} "
            f"{val:>{v}} "
            f"{pnl:>{p}} "
            f"{'':>{sz}} "
            f"{lev:>{l}} "
            f"{'':>{lq}} "
            f"{trv:>{t}}"
        )
    else:
        line = (
            f"{'':<{a}} "
            f"{'':<{s}} "
            f"{val:>{v}} "
            f"{pnl:>{p}} "
            f"{lev:>{l}} "
            f"{'':>{lq}} "
            f"{trv:>{t}}"
        )

    print(f"{color}{bold}{line}{RESET}")
