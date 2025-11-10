from __future__ import annotations
from typing import Any, Dict, List, Optional
import logging

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_below, body_indent_lines,
    paint_line, color_if_plain,
)

log = logging.getLogger("sonic.engine")

PANEL_SLUG = "positions"
PANEL_NAME = "Positions"

# ──────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ──────────────────────────────────────────────────────────────────────────────

def _first(*vals):
    for v in vals:
        if v not in (None, "", [], {}, ()):
            return v
    return None

def _num(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None

def _fmt_money(v: Any) -> str:
    n = _num(v)
    if n is None: return "-" if v in (None, "") else str(v)
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

def _to_mapping(item: Any) -> Dict[str, Any]:
    """Coerce PositionDB/Position (pydantic) or any model-like object into a dict."""
    if item is None:
        return {}
    md = getattr(item, "model_dump", None)      # pydantic v2
    if callable(md):
        try: return md()
        except Exception: pass
    md = getattr(item, "dict", None)            # pydantic v1
    if callable(md):
        try: return md()
        except Exception: pass
    d = getattr(item, "__dict__", None)         # generic
    return d if isinstance(d, dict) else {}

def _sym(d: Dict[str, Any]) -> str:
    # PositionDB: asset_type
    return str(_first(d.get("asset_type"), d.get("symbol"), d.get("asset"), d.get("name"), "—"))

# fixed widths for clean columns
W_ASSET = 8
W_SIZE  = 10
W_VAL   = 11
W_PNL   = 10
W_LEV   = 6
W_LIQ   = 6
W_HEAT  = 6
W_TRV   = 6

def _row_from_item(item: Any) -> str:
    """
    PositionDB-aware row:
      asset_type, size, value, pnl_after_fees_usd, leverage,
      liquidation_distance / liquidation_distance_pct,
      current_heat_index / heat_index, travel_percent
    """
    d = _to_mapping(item)
    asset = _sym(d)
    size  = _fmt_size(d.get("size"))
    val   = _fmt_money(d.get("value"))
    pnl   = _fmt_money(_first(d.get("pnl_after_fees_usd"), d.get("pnl"), d.get("unrealizedPnl")))
    lev   = _fmt_lev(d.get("leverage"))
    liq   = _fmt_pct(_first(d.get("liquidation_distance_pct"), d.get("liquidation_distance")))
    heat  = _fmt_pct(_first(d.get("current_heat_index"), d.get("heat_index")))
    trav  = _fmt_pct(_first(d.get("travel_percent"), d.get("travel")))
    return (
        f"{asset:<{W_ASSET}} "
        f"{size:>{W_SIZE}} "
        f"{val:>{W_VAL}} "
        f"{pnl:>{W_PNL}} "
        f"{lev:>{W_LEV}} "
        f"{liq:>{W_LIQ}} "
        f"{heat:>{W_HEAT}} "
        f"{trav:>{W_TRV}}"
    )

def _format_totals(items: List[Any]) -> str:
    size = value = pnl = 0.0
    levs: List[float] = []
    travs: List[float] = []
    for it in items:
        d = _to_mapping(it)
        v = _num(d.get("size"));                       size  += 0.0 if v is None else v
        v = _num(d.get("value"));                      value += 0.0 if v is None else v
        v = _num(_first(d.get("pnl_after_fees_usd"), d.get("pnl"))); pnl += 0.0 if v is None else v
        v = _num(d.get("leverage"));                   levs.append(v) if v is not None else None
        v = _num(_first(d.get("travel_percent"), d.get("travel"))); travs.append(v) if v is not None else None
    avg_lev  = sum(levs)/len(levs)   if levs  else None
    avg_trav = sum(travs)/len(travs) if travs else None
    return (
        f"{'Totals':<{W_ASSET}} "
        f"{_fmt_size(size):>{W_SIZE}} "
        f"{_fmt_money(value):>{W_VAL}} "
        f"{_fmt_money(pnl):>{W_PNL}} "
        f"{_fmt_lev(avg_lev):>{W_LEV}} "
        f"{'-':>{W_LIQ}} "
        f"{'-':>{W_HEAT}} "
        f"{_fmt_pct(avg_trav):>{W_TRV}}"
    )

def _get_items_from_manager(context: Dict[str, Any]) -> List[Any]:
    dl = context.get("dl")
    if not dl:
        return []
    mgr = getattr(dl, "positions", None) or getattr(dl, "dl_positions", None)
    if not mgr:
        return []

    items: Any = []
    getter = getattr(mgr, "get_all_positions", None)
    if callable(getter):
        try:
            items = getter()
        except Exception as e:
            log.info("[positions] positions manager get_all_positions() error: %s", e)
            items = []
    elif callable(getattr(mgr, "get_active_positions", None)):
        try:
            items = mgr.get_active_positions()  # type: ignore[call-arg]
        except Exception as e:
            log.info("[positions] positions manager get_active_positions() error: %s", e)
            items = []
    elif hasattr(mgr, "items"):
        items = getattr(mgr, "items") or []

    if not isinstance(items, list):
        return []
    return items

# ──────────────────────────────────────────────────────────────────────────────
# Render
# ──────────────────────────────────────────────────────────────────────────────

def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    out: List[str] = []  # always defined

    # Title
    out += emit_title_block(PANEL_SLUG, PANEL_NAME)

    body = get_panel_body_config(PANEL_SLUG)

    # Header
    header = (
        f"{'🪙Asset':<{W_ASSET}} "
        f"{'📦Size':>{W_SIZE}} "
        f"{'🟩Value':>{W_VAL}} "
        f"{'📈PnL':>{W_PNL}} "
        f"{'🧷Lev':>{W_LEV}} "
        f"{'💧Liq':>{W_LIQ}} "
        f"{'🔥Heat':>{W_HEAT}} "
        f"{'🧭Trave':>{W_TRV}}"
    )
    out += body_indent_lines(PANEL_SLUG, [paint_line(header, body["column_header_text_color"])])

    # Fetch strictly from DL manager
    items = _get_items_from_manager(context)
    source = "DL" if items else None

    log.info("[positions] source=%s count=%d", source or "NONE", len(items))

    if not items:
        out += body_indent_lines(PANEL_SLUG, ["(no positions)"])
        out += body_pad_below(PANEL_SLUG)
        return out

    # Rows
    for it in items:
        out += body_indent_lines(PANEL_SLUG, [color_if_plain(_row_from_item(it), body["body_text_color"])])

    # Totals
    out += body_indent_lines(PANEL_SLUG, [paint_line(_format_totals(items), body["totals_row_color"])])

    out += body_pad_below(PANEL_SLUG)
    return out
