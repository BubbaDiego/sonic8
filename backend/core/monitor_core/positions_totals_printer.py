from __future__ import annotations
from typing import Any, Dict, List, Optional, Sequence

RESET = "\n"
BOLD = "\x00"
ENDC = ""
COLOR = ""


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
      - dict-like with keys (case-insensitive): value, pnl, lev, travel
      - sequence of 7 columns: [asset, side, value, pnl, lev, liq, travel]
    """
    if isinstance(row, dict):
        return {
            "value": _as_float(_get_ci(row, "value")),
            "pnl": _as_float(_get_ci(row, "pnl")),
            "lev": _as_float(_get_ci(row, "lev")),
            "travel": _as_float(_get_ci(row, "travel")),
        }
    if isinstance(row, Sequence) and len(row) >= 7:
        return {
            "value": _as_float(row[2]),
            "pnl": _as_float(row[3]),
            "lev": _as_float(row[4]),
            "travel": _as_float(row[6]),
        }
    return {"value": None, "pnl": None, "lev": None, "travel": None}


def compute_weighted_totals(rows: List[Any]) -> Dict[str, Optional[float]]:
    """Sum(Value), sum(PnL), |Value|-weighted averages for Lev and Travel."""
    total_value = 0.0
    total_pnl = 0.0
    w_lev_num = w_lev_den = 0.0
    w_trv_num = w_trv_den = 0.0

    for r in rows:
        f = _extract_fields(r)
        v, p, l, t = f["value"], f["pnl"], f["lev"], f["travel"]
        if v is not None:
            total_value += v
            if l is not None:
                w_l = abs(v) * l
                w_lev_num += w_l
                w_lev_den += abs(v)
            if t is not None:
                w_t = abs(v) * t
                w_trv_num += w_t
                w_trv_den += abs(v)
        if p is not None:
            total_pnl += p

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
    width_map: Dict[str, int]
) -> None:
    """
    Print ONE aligned totals line in the same block, under the last row.
    Leave Asset/Side/Liq empty; fill Value/PnL/Lev/Travel.
    """
    line = (
        f"{'':<{width_map['asset']}} "
        f"{'':<{width_map['side']}} "
        f"{_fmt_money(totals.get('value')):>{width_map['value']}} "
        f"{_fmt_money(totals.get('pnl')):>{width_map['pnl']}} "
        f"{_fmt_lev(tals := totals.get('avg_lev', totals.get('avg_lev_weighted'))):>{width_map['lev']}} "
        f"{'':>{width_map['liq']}} "
        f"{_fmt_pct(totals.get('avg_travel', totals.get('avg_travel_weighted'))):>{width_map['travel']}}"
    )
    print(f"{BOLD}{line}{ENDC}")
