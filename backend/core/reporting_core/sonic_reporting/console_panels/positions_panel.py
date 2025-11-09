# backend/core/reporting_core/sonic_reporting/console_panels/positions_panel.py
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_above, body_pad_below, body_indent_lines,
    color_if_plain, paint_line,
)

PANEL_SLUG = "positions"
PANEL_NAME = "Positions"

# ---------- small helpers ----------
def _sd(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}

def _first(*vals):
    for v in vals:
        if v not in (None, "", [], {}, ()):
            return v
    return None

def _num(v: Any) -> Optional[float]:
    try:
        return float(v)
    except Exception:
        return None

def _fmt_money(v: Any) -> str:
    n = _num(v)
    if n is None:
        return "-" if v in (None, "") else str(v)
    sign = "-" if n < 0 else ""
    n = abs(n)
    return f"{sign}${n:,.2f}"

def _fmt_pct(v: Any) -> str:
    n = _num(v)
    return f"{n:.0f}%" if n is not None else "-"

def _fmt_lev(v: Any) -> str:
    n = _num(v)
    return f"{n:.1f}x" if n is not None else "—"

def _fmt_size(v: Any) -> str:
    n = _num(v)
    return f"{n:,.2f}" if n is not None else "-" if v in (None, "") else str(v)

def _sym(d: Dict[str, Any]) -> str:
    return str(_first(d.get("symbol"), d.get("asset"), d.get("sym"), d.get("name"), "—"))

# ---------- hard source: dl.dl_positions (or dl.positions) ----------
def _get_positions_manager(dl: Any):
    for attr in ("dl_positions", "positions"):
        if hasattr(dl, attr):
            return getattr(dl, attr)
    return None

def _iter_items_from_mgr(mgr: Any) -> Iterable[Dict[str, Any]]:
    """
    Strict manager read—NO fallbacks to csum/db/etc.
    Accepts common shapes:
      - method: get_items(), list_open(), all_open(), list(), all()
      - attribute: items, open
    """
    for name in ("get_items", "list_open", "all_open", "list", "all"):
        fn = getattr(mgr, name, None)
        if callable(fn):
            try:
                got = fn()
                if isinstance(got, list):
                    for it in got:
                        if isinstance(it, dict):
                            yield it
                    return
            except Exception:
                pass
    for attr in ("items", "open"):
        arr = getattr(mgr, attr, None)
        if isinstance(arr, list):
            for it in arr:
                if isinstance(it, dict):
                    yield it
            return

def _row_from_item(d: Dict[str, Any]) -> str:
    # columns: Asset | Size | Value | PnL | Lev | Liq | Heat | Trave
    asset = _sym(d)
    size  = _fmt_size(_first(d.get("size"), d.get("sizeUsd"), d.get("qty")))
    val   = _fmt_money(_first(d.get("valueUsd"), d.get("value"), d.get("notionalUsd")))
    pnl   = _fmt_money(_first(d.get("pnlUsd"), d.get("pnl"), d.get("unrealizedPnl")))
    lev   = _fmt_lev(_first(d.get("lev"), d.get("leverage")))
    liq   = _fmt_pct(_first(d.get("liqPct"), d.get("liquidationDistancePct"), d.get("liq_pct")))
    heat  = _fmt_pct(_first(d.get("heatPct"), d.get("heat"), d.get("riskPct")))
    trav  = _fmt_pct(_first(d.get("travelPct"), d.get("travel"), d.get("travePct"), d.get("trave")))
    return f"{asset:<8} {size:>9} {val:>10} {pnl:>9} {lev:>6} {liq:>6} {heat:>6} {trav:>6}"

def _totals_from_mgr(mgr: Any) -> Dict[str, Any]:
    """
    Try manager rollups first; if missing, compute from items we already iterated.
    Since we don't want to buffer, we’ll do a second pass via items() again if needed.
    """
    out = {"size": None, "value": None, "pnl": None, "avg_lev": None, "avg_travel": None}
    for k, names in {
        "size": ("total_size", "totalSize", "size_total", "sizeTotalUsd"),
        "value": ("total_value_usd", "totalValueUsd", "value_total_usd", "valueTotalUsd"),
        "pnl": ("total_pnl_usd", "totalPnlUsd", "pnl_total_usd", "pnlTotalUsd"),
        "avg_lev": ("avg_lev", "avgLeverage"),
        "avg_travel": ("avg_travel_pct", "avgTravelPct"),
    }.items():
        for n in names:
            if hasattr(mgr, n):
                out[k] = getattr(mgr, n)
                break

    # If totals missing, compute via a fresh pass.
    need_calc = any(out[k] is None for k in ("size", "value", "pnl"))
    if need_calc:
        size = value = pnl = 0.0
        had_any = False
        for it in _iter_items_from_mgr(mgr):
            had_any = True
            v_size = _num(_first(it.get("size"), it.get("sizeUsd")))
            v_val  = _num(_first(it.get("valueUsd"), it.get("value")))
            v_pnl  = _num(_first(it.get("pnlUsd"), it.get("pnl")))
            if v_size is not None:
                size += v_size
            if v_val is not None:
                value += v_val
            if v_pnl is not None:
                pnl += v_pnl
        if had_any:
            out["size"] = size
            out["value"] = value
            out["pnl"] = pnl

    return out

# ---------- render ----------
def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    out: List[str] = []  # always defined
    try:
        out += emit_title_block(PANEL_SLUG, PANEL_NAME)
        body = get_panel_body_config(PANEL_SLUG)

        # Strict source: DataLocker manager
        dl = context.get("dl")
        mgr = _get_positions_manager(dl) if dl is not None else None
        if mgr is None:
            out += body_indent_lines(PANEL_SLUG, ["[POSITIONS] missing dl.dl_positions / dl.positions — fix pipeline"])
            out += body_pad_below(PANEL_SLUG)
            return out

        # Header
        header = f"{'🪙Asset':<8} {'📦Size':>9} {'🟩Value':>10} {'📈PnL':>9} {'🧷Lev':>6} {'💧Liq':>6} {'🔥Heat':>6} {'🧭Trave':>6}"
        out += body_pad_above(PANEL_SLUG)
        out += body_indent_lines(PANEL_SLUG, [paint_line(header, body["column_header_text_color"])])

        # Rows
        any_row = False
        items = list(_iter_items_from_mgr(mgr))
        for d in items:
            out += body_indent_lines(PANEL_SLUG, [color_if_plain(_row_from_item(_sd(d)), body["body_text_color"])])
            any_row = True
        if not any_row:
            out += body_indent_lines(PANEL_SLUG, ["(no positions)"])

        # Totals
        totals = _totals_from_mgr(mgr)
        tot_line = f"{'Totals':<8} {_fmt_size(totals['size']):>9} {_fmt_money(totals['value']):>10} {_fmt_money(totals['pnl']):>9} {_fmt_lev(totals['avg_lev']):>6} {'—':>6} {'—':>6} {_fmt_pct(totals['avg_travel']):>6}"
        out += body_indent_lines(PANEL_SLUG, [paint_line(tot_line, body["totals_row_color"])])
        out += body_pad_below(PANEL_SLUG)
        return out
    except Exception as e:
        out.append(f"[REPORT] positions panel failed: {e}")
        return out
