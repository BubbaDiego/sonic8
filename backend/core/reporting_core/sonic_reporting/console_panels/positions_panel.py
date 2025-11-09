from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_above, body_pad_below, body_indent_lines,
    color_if_plain, paint_line,
)

PANEL_SLUG = "positions"
PANEL_NAME = "Positions"

# ───────────────────────────
# Little reflecty helpers
# ───────────────────────────

def _sd(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}

def _first(*vals):
    for v in vals:
        if v not in (None, "", [], {}, ()):
            return v
    return None

def _call_any(obj: Any, names: Iterable[str]) -> Any:
    for n in names:
        fn = getattr(obj, n, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                continue
    return None

def _get_any(obj: Any, names: Iterable[str]) -> Any:
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return None

# ───────────────────────────
# Formatters
# ───────────────────────────

def _fmt_money(v: Any) -> str:
    try:
        n = float(v)
        sign = "-" if n < 0 else ""
        n = abs(n)
        return f"{sign}${n:,.2f}"
    except Exception:
        return "-" if v in (None, "") else str(v)

def _fmt_pct(v: Any) -> str:
    try:
        n = float(v)
        return f"{n:.0f}%"
    except Exception:
        return "-" if v in (None, "") else str(v)

def _fmt_lev(v: Any) -> str:
    try:
        n = float(v)
        return f"{n:.1f}x"
    except Exception:
        return "—"

def _fmt_size(v: Any) -> str:
    try:
        n = float(v)
        return f"{n:,.2f}"
    except Exception:
        return "-" if v in (None, "") else str(v)

# ───────────────────────────
# Data sources — dl_positions FIRST
# ───────────────────────────

def _rows_from_dl_positions(ctx: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Prefer DataLocker-backed positions manager:
      ctx['dl'].dl_positions  (common)
      or methods like:
        - get_positions_items()
        - get_positions()
        - get_portfolio_positions()
        - list_open() / all_open() / all()
    """
    dl = ctx.get("dl")
    if not dl:
        return None

    # try a manager attribute first
    mgr = _get_any(dl, ("dl_positions", "positions", "positions_manager", "dl_pos", "pos_mgr"))
    if mgr:
        # method styles we’ll try on the manager
        got = _call_any(mgr, (
            "get_items", "get_positions_items", "list_open", "all_open", "list", "all",
            "open_items", "fetch_open"
        ))
        if isinstance(got, list) and (not got or isinstance(got[0], dict)):
            return got
        # some managers expose data directly as a list attribute
        arr = _get_any(mgr, ("items", "open", "rows"))
        if isinstance(arr, list) and (not arr or isinstance(arr[0], dict)):
            return arr

    # fall back to dl-level helpers
    got = _call_any(dl, ("get_positions_items", "get_positions", "get_portfolio_positions"))
    if isinstance(got, list) and (not got or isinstance(got[0], dict)):
        return got

    return None

def _prefmt_rows(ctx: Dict[str, Any]) -> Optional[List[str]]:
    rows = _first(ctx.get("positions_rows"), ctx.get("positions_lines"))
    if isinstance(rows, list) and (not rows or isinstance(rows[0], str)):
        return rows
    return None

# ───────────────────────────
# Row building
# ───────────────────────────

def _sym(d: Dict[str, Any]) -> str:
    return str(_first(d.get("symbol"), d.get("asset"), d.get("sym"), d.get("name"), "—"))

def _row_from_item(d: Dict[str, Any]) -> str:
    # columns: Asset | Size | Value | PnL | Lev | Liq | Heat | Trave
    asset = _sym(d)
    size  = _fmt_size(_first(d.get("size"), d.get("sizeUsd"), d.get("qty")))
    val   = _fmt_money(_first(d.get("valueUsd"), d.get("value"), d.get("notionalUsd")))
    pnl   = _fmt_money(_first(d.get("pnlUsd"), d.get("pnl"), d.get("unrealizedPnl")))
    lev   = _fmt_lev(_first(d.get("lev"), d.get("leverage")))
    liq   = _fmt_pct(_first(d.get("liqPct"), d.get("liquidationDistancePct"), d.get("liq"), d.get("liq_pct")))
    heat  = _fmt_pct(_first(d.get("heatPct"), d.get("heat"), d.get("riskPct")))
    trav  = _fmt_pct(_first(d.get("travelPct"), d.get("travel"), d.get("travePct"), d.get("trave")))
    return f"{asset:<8} {size:>9} {val:>10} {pnl:>9} {lev:>6} {liq:>6} {heat:>6} {trav:>6}"

def _iter_position_rows(ctx: Dict[str, Any]) -> Iterable[str]:
    # preformatted wins if you’ve already rendered elsewhere
    pref = _prefmt_rows(ctx)
    if pref is not None:
        for ln in pref:
            yield ln
        return

    items = _rows_from_dl_positions(ctx) or []
    for d in items:
        yield _row_from_item(_sd(d))

def _totals_from_dl(ctx: Dict[str, Any]) -> Tuple[str, str, str, str, str, str, str, str]:
    dl = ctx.get("dl")
    tot_size = tot_val = tot_pnl = avg_lev = avg_trv = None
    if dl:
        # look for rollups on manager first
        mgr = _get_any(dl, ("dl_positions", "positions", "positions_manager", "dl_pos", "pos_mgr"))
        if mgr:
            tot_size = _get_any(mgr, ("total_size", "totalSize", "size_total", "sizeTotalUsd"))
            tot_val  = _get_any(mgr, ("total_value_usd", "totalValueUsd", "value_total_usd", "valueTotalUsd"))
            tot_pnl  = _get_any(mgr, ("total_pnl_usd", "totalPnlUsd", "pnl_total_usd", "pnlTotalUsd"))
            avg_lev  = _get_any(mgr, ("avg_lev", "avgLeverage"))
            avg_trv  = _get_any(mgr, ("avg_travel_pct", "avgTravelPct"))

        # if rollups aren’t available, compute from items
        if tot_size is None or tot_val is None or tot_pnl is None:
            items = _rows_from_dl_positions(ctx) or []
            try:
                if tot_size is None:
                    tot_size = sum(float(_sd(i).get("size") or 0.0) for i in items)
                if tot_val is None:
                    tot_val = sum(float(_sd(i).get("valueUsd") or 0.0) for i in items)
                if tot_pnl is None:
                    tot_pnl = sum(float(_sd(i).get("pnlUsd") or 0.0) for i in items)
            except Exception:
                pass

    return (
        "Totals",
        _fmt_size(tot_size),
        _fmt_money(tot_val),
        _fmt_money(tot_pnl),
        _fmt_lev(avg_lev),
        "—", "—",
        _fmt_pct(avg_trv),
    )

def _format_totals(ctx: Dict[str, Any]) -> str:
    t = _totals_from_dl(ctx)
    return f"{t[0]:<8} {t[1]:>9} {t[2]:>10} {t[3]:>9} {t[4]:>6} {t[5]:>6} {t[6]:>6} {t[7]:>6}"

# ───────────────────────────
# Render (no C-sum, no crash)
# ───────────────────────────

def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    out: List[str] = []   # ALWAYS defined first; never shadow
    try:
        # Title block (rounded + width/padding from config)
        out += emit_title_block(PANEL_SLUG, PANEL_NAME)

        body = get_panel_body_config(PANEL_SLUG)
        header = f"{'🪙Asset':<8} {'📦Size':>9} {'🟩Value':>10} {'📈PnL':>9} {'🧷Lev':>6} {'💧Liq':>6} {'🔥Heat':>6} {'🧭Trave':>6}"

        out += body_pad_above(PANEL_SLUG)
        out += body_indent_lines(PANEL_SLUG, [paint_line(header, body["column_header_text_color"])])

        any_row = False
        for line in _iter_position_rows(context):
            out += body_indent_lines(PANEL_SLUG, [color_if_plain(line, body["body_text_color"])])
            any_row = True
        if not any_row:
            out += body_indent_lines(PANEL_SLUG, ["(no positions)"])

        out += body_indent_lines(PANEL_SLUG, [paint_line(_format_totals(context), body["totals_row_color"])])
        out += body_pad_below(PANEL_SLUG)
        return out
    except Exception as e:
        out.append(f"[REPORT] positions panel failed: {e}")
        return out
