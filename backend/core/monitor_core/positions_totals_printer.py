from __future__ import annotations
from typing import Any, Dict, List, Optional, Sequence

# Simple ANSI styling for highlight; adjust if you already have constants
RESET = "\x1b[0m"
BOLD = "\x1b[1m"
LINE_COLOR = "\x1b[38;5;45m"  # cyan-ish; tweak to taste (e.g. "\x1b[97m" bright white)

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
            m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
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
            8-col: [Asset, Side, Value, PnL, Size, Lev, Liq, Travel]   <-- preferred
    Returns numeric fields (None when not parseable).
    """
    if isinstance(row, dict):
        size = _as_float(_get_ci(row, "size")) or _as_float(_get_ci(row, "qty")) or _as_float(_get_ci(row, "amount")) or _as_float(_get_ci(row, "position_size"))
        return {
            "value":  _as_float(_get_ci(row, "value")),
            "pnl":    _as_float(_get_ci(row, "pnl")),
            "size":   size,
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
            # [asset, side, value, pnl, lev, liq, travel] (no explicit size)
            return {
                "value":  _as_float(row[2]),
                "pnl":    _as_float(row[3]),
                "size":   None,                 # will fallback to value
                "lev":    _as_float(row[4]),
                "travel": _as_float(row[6]),
            }
    return {"value": None, "pnl": None, "size": None, "lev": None, "travel": None}

def compute_weighted_totals(rows: List[Any]) -> Dict[str, Optional[float]]:
    """
    Compute ΣValue, ΣPnL, and |Size|-weighted averages for Lev and Travel.
    If Size is absent for a row, we fallback to |Value| for that row only.
    """
    total_value = 0.0
    total_pnl = 0.0
    w_lev_num = w_lev_den = 0.0
    w_trv_num = w_trv_den = 0.0

    for r in rows:
        f = _extract_fields(r)
        v, p, s, l, t = f["value"], f["pnl"], f["size"], f["lev"], f["travel"]
        # sums
        if v is not None:
            total_value += v
        if p is not None:
            total_pnl += p
        # weights by |size| if possible, else by |value|
        w = None
        if s is not None:
            w = abs(s)
        elif v is not None:
            w = abs(v)
        if w is not None:
            if l is not None:
                w_lev_num += w * l
                w_lev_den += w
            if t is not None:
                w_trv_num += w * t
                w_trv_den += w

    lev_w = (w_lev_num / w_lev_den) if w_lev_den > 0 else None
    trv_w = (w_trv_num / w_trv_den) if w_trv_den > 0 else None
    return {"value": total_value, "pnl": total_pnl, "avg_lev_weighted": lev_w, "avg_travel_weighted": trv_w}

def _fmt_money(v: Optional[float]) -> str:
    return f"${v:,.2f}" if isinstance(v, float) else "-"

def _fmt_lev(v: Optional[float]) -> str:
    return f"{v:.2f}×" if isinstance(v, float) else "-"

def _fmt_pct(v: Optional[float]) -> str:
    return f"{v:.2f}%" if isinstance(v, float) else "-"

def print_positions_totals_line(totals: Dict[str, Optional[float]], width_map: Dict[str, int]) -> None:
    """
    Print ONE aligned totals line directly under the last Positions row.
    Columns (with Size inserted between PnL and Lev): Asset | Side | Value | PnL | Size | Lev | Liq | Travel
    We leave Asset/Side/Liq blank; fill Value/PnL/Lev/Travel; Size can be left blank or show 'Σ' if you want.
    """
    val = _fmt_money(totals.get("value"))
    pnl = _fmt_money(totals.get("pnl"))
    lev = _fmt_lev(totals.get("avg_lev_weighted"))
    trv = _fmt_pct(totals.get("avg_travel_weighted"))

    # single aligned line (no extra banners)
    line = (
        f"{'':<{width_map['asset']}} "
        f"{'':<{width_map['side']}} "
        f"{val:>{width_map['value']}} "
        f"{pnl:>{width_map['pnl']}} "
        f"{'':>{width_map['size']}} "     # leave Size footer cell empty by default
        f"{lev:>{width_map['lev']}} "
        f"{'':>{width_map['liq']}} "
        f"{trv:>{width_map['travel']}}"
    )
    print(f"{LINE_COLOR}{BOLD}{line}{RESET}", end="")
