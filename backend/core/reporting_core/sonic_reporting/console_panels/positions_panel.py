from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple
import math

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_above, body_pad_below, body_indent_lines,
    color_if_plain, paint_line,
)

PANEL_SLUG = "positions"
PANEL_NAME = "Positions"

# ──────────────────────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────────────────────

def _sd(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}

def _first(*vals):
    for v in vals:
        if v not in (None, "", [], {}, ()):
            return v
    return None

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

def _dash(v: Any) -> str:
    return "—" if v in (None, "", "-", "—") else str(v)

# ──────────────────────────────────────────────────────────────────────────────
# Data extraction
# We try several shapes so this panel works even if upstream writers vary.
# Priority: csum.portfolio.positions.items → csum.positions.items → preformatted rows → DL helpers
# ──────────────────────────────────────────────────────────────────────────────

def _iter_csum_positions(ctx: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    csum = _sd(ctx.get("csum"))
    # portfolio form
    items = _first(
        _sd(_sd(csum.get("portfolio")).get("positions")).get("items"),
        _sd(csum.get("positions")).get("items"),
        csum.get("positions_items"),
    )
    if isinstance(items, list) and (not items or isinstance(items[0], dict)):
        return items
    return None

def _iter_prefmt_rows(ctx: Dict[str, Any]) -> Optional[List[str]]:
    # if someone already built printable lines
    rows = _first(ctx.get("positions_rows"), ctx.get("positions_lines"))
    if isinstance(rows, list) and (not rows or isinstance(rows[0], str)):
        return rows
    return None

def _dl_fallback(ctx: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    dl = ctx.get("dl")
    if not dl:
        return None
    for name in ("get_positions_items", "get_positions", "get_portfolio_positions"):
        fn = getattr(dl, name, None)
        if callable(fn):
            try:
                vals = fn()
                if isinstance(vals, list) and (not vals or isinstance(vals[0], dict)):
                    return vals
            except Exception:
                pass
    return None

# ──────────────────────────────────────────────────────────────────────────────
# Row building
# Expect dict items with flexible keys; we normalize the usual suspects.
# Keys we try: symbol/asset, size,sizeUsd, valueUsd, pnlUsd, lev/leverage, liqPct, heatPct, travelPct, entryPrice/markPrice
# ──────────────────────────────────────────────────────────────────────────────

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
    prefmt = _iter_prefmt_rows(ctx)
    if prefmt is not None:
        for line in prefmt:
            yield line
        return

    items = _iter_csum_positions(ctx) or _dl_fallback(ctx) or []
    for d in items:
        yield _row_from_item(_sd(d))

def _totals(ctx: Dict[str, Any]) -> Tuple[str, str, str, str, str, str, str, str]:
    # Compute a few soft totals; if numbers are missing, show dashes.
    csum = _sd(ctx.get("csum"))
    # try portfolio rollups first
    port = _sd(csum.get("portfolio"))
    tot_size = _first(port.get("totalSize"), port.get("sizeTotalUsd"))
    tot_val  = _first(port.get("totalValueUsd"), port.get("valueTotalUsd"))
    tot_pnl  = _first(port.get("totalPnlUsd"), port.get("pnlTotalUsd"))

    # fallback: sum from items if present
    if tot_size is None or tot_val is None or tot_pnl is None:
        items = _iter_csum_positions(ctx) or _dl_fallback(ctx) or []
        try:
            if tot_size is None:
                tot_size = sum(float(_sd(i).get("size") or 0) for i in items)
            if tot_val is None:
                tot_val  = sum(float(_sd(i).get("valueUsd") or 0) for i in items)
            if tot_pnl is None:
                tot_pnl  = sum(float(_sd(i).get("pnlUsd") or 0) for i in items)
        except Exception:
            pass

    # avg leverage if available
    avg_lev = _first(port.get("avgLeverage"), port.get("avgLev"))
    avg_trv = _first(port.get("avgTravelPct"), port.get("avg_travel"))

    return (
        "Totals",
        _fmt_size(tot_size),
        _fmt_money(tot_val),
        _fmt_money(tot_pnl),
        _fmt_lev(avg_lev),
        "—",
        "—",
        _fmt_pct(avg_trv),
    )

def _format_totals(ctx: Dict[str, Any]) -> str:
    t = _totals(ctx)
    return f"{t[0]:<8} {t[1]:>9} {t[2]:>10} {t[3]:>9} {t[4]:>6} {t[5]:>6} {t[6]:>6} {t[7]:>6}"

# ──────────────────────────────────────────────────────────────────────────────
# Render
# ──────────────────────────────────────────────────────────────────────────────

def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    """
    Robust renderer:
      - out always defined
      - never crashes on missing fields
      - uses body theming and spacing-after only
    """
    out: List[str] = []  # ALWAYS define first
    try:
        # title
        out += emit_title_block(PANEL_SLUG, PANEL_NAME)

        body_cfg = get_panel_body_config(PANEL_SLUG)

        # header
        header = f"{'🪙Asset':<8} {'📦Size':>9} {'🟩Value':>10} {'📈PnL':>9} {'🧷Lev':>6} {'💧Liq':>6} {'🔥Heat':>6} {'🧭Trave':>6}"
        out += body_pad_above(PANEL_SLUG)
        out += body_indent_lines(PANEL_SLUG, [paint_line(header, body_cfg["column_header_text_color"])])

        # rows
        any_row = False
        for line in _iter_position_rows(context):
            out += body_indent_lines(PANEL_SLUG, [color_if_plain(line, body_cfg["body_text_color"])])
            any_row = True
        if not any_row:
            out += body_indent_lines(PANEL_SLUG, ["(no positions)"])

        # totals
        out += body_indent_lines(PANEL_SLUG, [paint_line(_format_totals(context), body_cfg["totals_row_color"])])

        # only spacing AFTER
        out += body_pad_below(PANEL_SLUG)
        return out
    except Exception as e:
        out.append(f"[REPORT] positions panel failed: {e}")
        return out
