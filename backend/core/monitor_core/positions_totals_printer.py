from __future__ import annotations

from typing import Dict, Any

# Simple ANSI color helpers (Windows Terminal supports ANSI; if not, it will just print raw)
RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
# Pick a distinct line color; teal-ish bright:
TOT_COLOR = "\x1b[38;5;45m"  # cyan-like
# If you’d prefer high-contrast white:
# TOT_COLOR = "\x1b[97m"

def _fmt_money(v):
    return f"${v:,.2f}" if isinstance(v, (int, float)) else "-"

def _fmt_lev(v):
    return f"{v:.2f}x" if isinstance(v, (int, float)) else "-"

def _fmt_pct(v):
    return f"{v:.2f}%" if isinstance(v, (int, float)) else "-"

def print_positions_totals_line(totals: Dict[str, Any], width_map: Dict[str, int] | None = None) -> None:
    """
    Prints a colored totals row that aligns under: Asset | Side | Value | PnL | Lev | Liq | Travel
    We only populate columns that make sense to aggregate.
    """
    tv = totals.get("value")
    tp = totals.get("pnl")
    tl = totals.get("avg_lev_weighted")
    tt = totals.get("avg_travel_weighted")

    val = _fmt_money(tv)
    pnl = _fmt_money(tp)
    lev = _fmt_lev(tl)
    trv = _fmt_pct(tt)

    # Default widths per screenshot vibe; override by passing a width_map if you have exact table widths.
    widths = width_map or {
        "asset": 5,
        "side": 6,
        "value": 10,
        "pnl": 10,
        "lev": 8,
        "liq": 8,
        "travel": 8,
    }

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
