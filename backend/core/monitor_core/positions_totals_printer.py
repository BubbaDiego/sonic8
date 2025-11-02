from __future__ import annotations

from typing import Any, Dict, List, Optional

# ANSI styling
RESET = "\x1b[0m"
BOLD = "\x1b[1m"
TOT_COLOR = "\x1b[38;5;45m"  # cyan-ish; switch to "\x1b[97m" for bright white


def _as_float(x: Any) -> Optional[float]:
    """Coerce numbers and formatted strings like '$1,234.56', '12.3%', '10.5x'."""
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        for ch in ("$", ",", "%", "x", "X"):
            s = s.replace(ch, "")
        s = s.replace("\u2013", "-")  # en-dash → minus
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


def compute_weighted_totals(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Sum Value/PnL; compute |Value|-weighted Lev and Travel from the same rows you print."""
    total_value = 0.0
    total_pnl = 0.0
    w_lev_num = w_lev_den = 0.0
    w_trv_num = w_trv_den = 0.0

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
        if pnl is not None:
            total_pnl += pnl

    return {
        "value": total_value,
        "pnl": total_pnl,
        "avg_lev_weighted": (w_lev_num / w_lev_den) if w_lev_den > 0 else None,
        "avg_travel_weighted": (w_trv_num / w_trv_den) if w_trv_den > 0 else None,
    }


def _fmt_money(v: Optional[float]) -> str:
    return f"${v:,.2f}" if isinstance(v, float) else "-"


def _fmt_lev(v: Optional[float]) -> str:
    return f"{v:.2f}x" if isinstance(v, float) else "-"


def _fmt_pct(v: Optional[float]) -> str:
    return f"{v:.2f}%" if isinstance(v, float) else "-"


def print_positions_totals_line(totals: Dict[str, Any], width_map: Dict[str, int] | None = None) -> None:
    """Print a colored totals row under: Asset | Side | Value | PnL | Lev | Liq | Travel."""
    widths = width_map or {"asset": 5, "side": 6, "value": 10, "pnl": 10, "lev": 8, "liq": 8, "travel": 8}
    val = _fmt_money(_as_float(totals.get("value")))
    pnl = _fmt_money(_as_float(totals.get("pnl")))
    lev = _fmt_lev(_as_float(totals.get("avg_lev_weighted")))
    trv = _fmt_pct(_as_float(totals.get("avg_travel_weighted")))
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
