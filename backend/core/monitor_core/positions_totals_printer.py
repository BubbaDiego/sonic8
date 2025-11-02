from __future__ import annotations
from typing import Any, Dict, List, Optional, Sequence

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
TOT_COLOR = "\x1b[38;5;45m"  # cyan-ish; change to "\x1b[97m" for bright white


def _as_float(x: Any) -> Optional[float]:
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        for ch in ("$", ",", "%", "x", "X"):
            s = s.replace(ch, "")
        s = s.replace("\u2013", "-")
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
    lk = key.lower()
    for k, v in d.items():
        if isinstance(k, str) and k.lower() == lk:
            return v
    return None


def _extract_fields(row: Any) -> Dict[str, Optional[float]]:
    """
    Accept either:
      - dict-like with keys (CI): value, pnl, lev, travel, side
      - sequence: [Asset, Side, Value, PnL, Lev, Liq, Travel]
    """
    if isinstance(row, dict):
        return {
            "value": _as_float(_get_ci(row, "value")),
            "pnl": _as_float(_get_ci(row, "pnl")),
            "lev": _as_float(_get_ci(row, "lev")),
            "travel": _as_float(_get_ci(row, "travel")),
            "side": str(_get_ci(row, "side") or "").upper(),
        }
    if isinstance(row, Sequence) and len(row) >= 7:
        # 0 Asset, 1 Side, 2 Value, 3 PnL, 4 Lev, 5 Liq, 6 Travel
        return {
            "value": _as_float(row[2]),
            "pnl": _as_float(row[3]),
            "lev": _as_float(row[4]),
            "travel": _as_float(row[6]),
            "side": str(row[1]).upper() if row[1] is not None else "",
        }
    return {"value": None, "pnl": None, "lev": None, "travel": None, "side": ""}


def compute_weighted_totals(rows: List[Any]) -> Dict[str, Any]:
    count = len(rows)
    total_value = 0.0
    total_pnl = 0.0
    gross = 0.0
    net = 0.0
    long_val = 0.0
    short_val = 0.0

    w_lev_num = w_lev_den = 0.0
    w_trv_num = w_trv_den = 0.0

    for r in rows:
        f = _extract_fields(r)
        v, p, l, t, side = f["value"], f["pnl"], f["lev"], f["travel"], f["side"]

        if v is not None:
            total_value += v
            gross += abs(v)
            net += v
            if side == "SHORT":
                short_val += v
            else:
                long_val += v

            if l is not None:
                w_lev_num += abs(v) * l
                w_lev_den += abs(v)
            if t is not None:
                w_trv_num += abs(v) * t
                w_trv_den += abs(v)

        if p is not None:
            total_pnl += p

    return {
        "count": count,
        "value": total_value,
        "pnl": total_pnl,
        "gross_exposure": gross,
        "net_exposure": net,
        "value_long": long_val,
        "value_short": short_val,
        "avg_lev_weighted": (w_lev_num / w_lev_den) if w_lev_den > 0 else None,
        "avg_travel_weighted": (w_trv_num / w_trv_den) if w_trv_den > 0 else None,
    }


def _fmt_money(v: Optional[float]) -> str:
    return f"${v:,.2f}" if isinstance(v, float) else "-"


def _fmt_lev(v: Optional[float]) -> str:
    return f"{v:.2f}x" if isinstance(v, float) else "-"


def _fmt_pct(v: Optional[float]) -> str:
    return f"{v:.2f}%" if isinstance(v, float) else "-"


def print_positions_totals_block(
    totals: Dict[str, Any],
    width_map: Dict[str, int] | None = None
) -> None:
    """
    Two-line totals block, aligned under columns (Asset|Side|Value|PnL|Lev|Liq|Travel):
      line 1: labeled totals (Value, PnL, W-Avg Lev, W-Avg Travel)
      line 2: extras (Count, Gross, Net, Long/Short)
    """
    widths = width_map or {"asset": 5, "side": 6, "value": 10, "pnl": 10, "lev": 8, "liq": 8, "travel": 8}

    # First line aligned to main columns
    label = "Totals:"
    val = _fmt_money(_as_float(totals.get("value")))
    pnl = _fmt_money(_as_float(totals.get("pnl")))
    lev = _fmt_lev(_as_float(totals.get("avg_lev_weighted")))
    trv = _fmt_pct(_as_float(totals.get("avg_travel_weighted")))

    line1 = (
        f"{label:<{widths['asset']}} "
        f"{'':<{widths['side']}} "
        f"{val:>{widths['value']}} "
        f"{pnl:>{widths['pnl']}} "
        f"{lev:>{widths['lev']}} "
        f"{'':>{widths['liq']}} "
        f"{trv:>{widths['travel']}}"
    )
    print(f"{BOLD}{TOT_COLOR}{line1}{RESET}")

    # Second line: extras
    cnt = totals.get("count", 0)
    gross = _fmt_money(_as_float(totals.get("gross_exposure")))
    net = _fmt_money(_as_float(totals.get("net_exposure")))
    vlong = _fmt_money(_as_float(totals.get("value_long")))
    vshort = _fmt_money(_as_float(totals.get("value_short")))

    extras = f"Count {cnt}  Gross {gross}  Net {net}  Long {vlong} / Short {vshort}"
    print(f"{BOLD}{TOT_COLOR}{extras}{RESET}")
