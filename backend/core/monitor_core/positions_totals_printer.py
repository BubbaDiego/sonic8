from __future__ import annotations
from typing import Any, Dict, List, Optional, Sequence

# Simple ANSI styling for highlight; tweak or blank out if you don’t want color/bold
RESET = "\x1b[0m"
BOLD = "\x1b[1m"
LINE_COLOR = "\x1b[38;5;45m"  # cyan-ish; change as desired, or set to "" for no color

def _as_float(x: Any) -> Optional[float]:
    """Coerce numbers and strings like '$1,234.56', '12.3%', '10.5x', '9.90×' into floats."""
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        for ch in ("$", ",", "%", "x", "X", "×"):
            s = s.replace(ch, "")
        s = s.replace("\u2013", "-")  # normalize en-dash
        try:
            return float(s)
        except Exception:
            import re
            m = re.search(r"[-+]?\d+(?:\.\b)?", s)
            m = m or re.search(r"[-+]?\d+(?:\.\d+)?", s)
            if m:
                try:
                    return float(m.group(0))
                except Exception:
                    return None
    return None

def _get_ci(d: Dict[str, Any], key: str) -> Any:
    """Case-insensitive dict access."""
    lk = key.lower()
    for k, v in d.items():
        if isinstance(k, str) and k.lower() == lk:
            return v
    return None

def _extract_fields(row: Any) -> Dict[str, Optional[float]]:
    """
    Accept either:
      - dict-like with keys (case-insensitive): value, pnl, size, lev, travel
      - sequence with 7 or 8 columns:
          7-col: [Asset, Side, Value, PnL, Lev, Liq, Travel]
          8-col: [Asset, Side, Value, PnL, Size, Lev, Liq, Travel]  <-- preferred
    Returns numeric fields (None when not parseable).
    """
    if isinstance(row, dict):
        size = (_as_float(_get_ci(row, "size"))
                or _as_float(_get_ci(row, "qty"))
                or _as_float(_get_ci(row, "amount"))
                or _as_float(_get_ci(row, "position_size")))
        return {
            "value":  _as_float(_get_ci(row, "value")),
            "pnl":    _as_float(_get_ci(row, "pnl")),
            "size":   size,                        # used as weight when present
            "lev":    _as_float(_get_ci(row, "lev")),
            "travel": _as_float(_get_ci(row, "travel")),
        }
    if isinstance(row, Sequence):
        if len(row) >= 8:
            # [asset, side, value, pnl, size, lev, liq, travel]
            return {
                "value":  _as_float(row[2]),
                "pnl":    _as_float(row[3]),
                "size":   _as_float(row[4]),
                "lev":    _as_float(row[5]),
                "travel": _as_float(row[7]),
            }
        if len(row) >= 7:
            # legacy 7-col rows (no size column) – fallback to weighting by Value for those rows only
            return {
                "value":  _as_float(row[2]),
                "pnl":    _as_float(row[3]),
                "size":   None,                     # fallback to |value| for weighting
                "lev":    _as_float(row[4]),
                "travel": _as_float(row[6]),
            }
    return {"value": None, "pnl": None, "size": None, "lev": None, "travel": None}

def compute_weighted_totals(rows: List[Any]) -> Dict[str, Optional[float]]:
    """
    Compute ΣValue, ΣPnL, and |Size|-weighted averages for Lev and Travel.
    If a row has no Size, weight that row by |Value| to avoid dropping it.
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

        weight = None
        if s is not None:
            weight = abs(s)
        elif v is not None:
            weight = abs(v)

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
        "avg_travel_weighted": trv_w
    }

def _fmt_money(v: Optional[float]) -> str:
    if isinstance(v, (int, float)):
        return f"${float(v):,.2f}"
    return "-"

def _fmt_lev(v: Optional[float]) -> str:
    if isinstance(v, (int, float)):
        return f"{float(v):.2f}×"
    return "-"

def _fmt_pct(v: Optional[float]) -> str:
    if isinstance(v, (int, float)):
        return f"{float(v):.2f}%"
    return "-"

def print_positions_totals_line(totals: Dict[str, Optional[float]], width_map: Dict[str, int]) -> None:
    """
    Print ONE aligned totals line directly under the last Positions row (no extra section).
    Columns (with Size): Asset | Side | Value | PnL | Size | Lev | Liq | Travel
    - Asset, Side, Liq cells left blank by design.
    - Value, PnL are straight sums.
    - Lev and Travel are size-weighted averages.
    """
    val = _fmt_money(totals.get("value"))
    pnl = _fmt_money(totals.get("pnl"))
    lev = _fmt_lev(totals.get("avg_lev", totals.get("avg_lev_weighted")))
    trv = _fmt_pct(totals.get("avg_travel", totals.get("avg_travel_weighted")))

    line = (
        f"{'':<{width_map['a']}} "
        f"{'':<{width_map['s']}} "
        f"{val:>{width_map['v']}} "
        f"{pnl:>{width_map['p']}} "
        f"{'':>{width_map['sz']}} "      # Size footer intentionally left blank (ΣSize optional)
        f"{lev:>{width_map['l']}} "
        f"{'':>{width_map['liq']}} "
        f"{trv:>{width_map['t']}}"
    )
    print(f"{LINE_COLOR}{BOLD}{line}{RESET}")
