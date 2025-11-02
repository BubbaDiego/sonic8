# backend/core/monitor_core/positions_totals_printer.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

# ANSI styling (Windows Terminal supports ANSI; harmless if unsupported)
RESET = "\x1b[0m"
BOLD = "\x1b[1m"
TOT_COLOR = "\x1b[38;5;45m"  # cyan-ish; change to "\x1b[97m" for bright white, etc.


def _as_float(x: Any) -> Optional[float]:
    """Robust coercion: handles numbers, '$1,234.56', '12.34%', '10.5x', etc."""
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        # common cosmetics
        for ch in ("$", ",", "%", "x", "X"):
            s = s.replace(ch, "")
        # Some formats like '–' or trailing spaces
        s = s.replace("\u2013", "-")  # en dash
        try:
            return float(s)
        except Exception:
            # Last resort: extract first numeric token (handles things like 'PnL: -12.3 USD')
            import re

            m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
            if m:
                try:
                    return float(m.group(0))
                except Exception:
                    return None
    return None


def _get_ci(d: Dict[str, Any], key: str) -> Any:
    """Case-insensitive dict access for keys like value/Value/VALUE."""
    lk = key.lower()
    for k, v in d.items():
        if isinstance(k, str) and k.lower() == lk:
            return v
    return None


def compute_weighted_totals(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute footer totals directly from the same rows you print:
      - Sum(value), Sum(pnl)
      - Weighted avg leverage by |value|
      - Weighted avg travel% by |value|
    Works whether row fields are numeric or formatted strings.
    Expected keys (case-insensitive): value, pnl, lev, travel.
    """
    total_value = 0.0
    total_pnl = 0.0

    w_lev_num = 0.0
    w_lev_den = 0.0

    w_trv_num = 0.0
    w_trv_den = 0.0

    long_val = 0.0
    short_val = 0.0

    for r in rows:
        v = _as_float(_get_ci(r, "value"))
        pnl = _as_float(_get_ci(r, "pnl"))
        lev = _as_float(_get_ci(r, "lev"))
        trv = _as_float(_get_ci(r, "travel"))

        if v is not None:
            total_value += v
            if lev is not None:
                w_lev_num += abs(v) * lev
                w_lev_den += abs(v)
            if trv is not None:
                w_trv_num += abs(v) * trv
                w_trv_den += abs(v)

            side = _get_ci(r, "side")
            if isinstance(side, str) and side.strip().upper() == "SHORT":
                short_val += v
            else:
                long_val += v

        if pnl is not None:
            total_pnl += pnl

    avg_lev_weighted = (w_lev_num / w_lev_den) if w_lev_den > 0 else None
    avg_travel_weighted = (w_trv_num / w_trv_den) if w_trv_den > 0 else None

    return {
        "count": len(rows),
        "value": total_value,
        "pnl": total_pnl,
        "value_long": long_val,
        "value_short": short_val,
        "avg_lev_weighted": avg_lev_weighted,
        "avg_travel_weighted": avg_travel_weighted,
    }


def _fmt_money(v: Optional[float]) -> str:
    return f"${v:,.2f}" if isinstance(v, float) else "-"


def _fmt_lev(v: Optional[float]) -> str:
    return f"{v:.2f}x" if isinstance(v, float) else "-"


def _fmt_pct(v: Optional[float]) -> str:
    return f"{v:.2f}%" if isinstance(v, float) else "-"


def print_positions_totals_line(
    totals: Dict[str, Any], width_map: Dict[str, int] | None = None
) -> None:
    """
    Print a colored totals row aligned under: Asset | Side | Value | PnL | Lev | Liq | Travel
    Only aggregable columns are populated.
    """
    widths = width_map or {
        "asset": 5,
        "side": 6,
        "value": 10,
        "pnl": 10,
        "lev": 8,
        "liq": 8,
        "travel": 8,
    }

    val = _fmt_money(_as_float(totals.get("value")))
    pnl = _fmt_money(_as_float(totals.get("pnl")))
    lev = _fmt_lev(_as_float(totals.get("avg_lev_weighted")))
    trv = _fmt_pct(_as_float(totals.get("avg_travel_weighted")))

    # Leave Asset/Side/Liq blank in footer row
    line = (
        f"{'':<{widths['asset']}} "
        f"{'':<{widths['side']}} "
        f"{val:>{widths['value']}} "
        f"{pnl:>{widths['pnl']}} "
        f"{lev:>{widths['lev']}} "
        f"{'':>{widths['liq']}} "
        f"{trv:>{widths['travel']}}"
    )
    print(f"{BOLD}{TOT_COLOR}{line}{RESET}")
