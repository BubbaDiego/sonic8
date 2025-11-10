from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Tuple
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

# ──────────────────────────────────────────────────────────────────────────────
# Source selection: PositionCore (preferred) → DL manager (fallback)
# ──────────────────────────────────────────────────────────────────────────────

def _import_position_core() -> Tuple[Any, str]:
    """
    Try several common module paths for PositionCore and return (class, module_path).
    We log which one succeeded to help diagnose.
    """
    candidates = (
        "backend.core.positions_core.position_core",
        "backend.core.positions_core.core",
        "backend.core.position_core",
        "backend.positions.position_core",
        "backend.core.portfolio_core.position_core",
    )
    last_err = None
    for mod in candidates:
        try:
            m = __import__(mod, fromlist=["PositionCore"])
            if hasattr(m, "PositionCore"):
                return m.PositionCore, mod
        except Exception as e:
            last_err = e
            continue
    raise ImportError(f"PositionCore not found; tried {candidates}; last error: {last_err}")

def _get_items_from_core(context: Dict[str, Any]) -> Tuple[List[Any], Optional[str]]:
    """
    Try PositionCore.get_active_positions() as classmethod or instance method.
    Returns (items, module_path or None).
    """
    try:
        PositionCore, modpath = _import_position_core()
    except Exception as e:
        log.info("[positions] PositionCore import failed: %s", e)
        return [], None

    dl  = context.get("dl")
    cfg = context.get("cfg") or context.get("config")

    # classmethod styles
    for arg in (dl, cfg, None):
        try:
            if hasattr(PositionCore, "get_active_positions"):
                res = PositionCore.get_active_positions(arg) if arg is not None else PositionCore.get_active_positions()  # type: ignore
                if isinstance(res, list) and res:
                    return res, modpath
        except TypeError:
            pass
        except Exception as e:
            log.info("[positions] PositionCore.get_active_positions class-method error: %s", e)
            break

    # instance styles
    for arg in (dl, cfg, None):
        try:
            core = PositionCore(arg) if arg is not None else PositionCore()  # type: ignore
            if hasattr(core, "get_active_positions"):
                res = core.get_active_positions()  # type: ignore
                if isinstance(res, list) and res:
                    return res, modpath
        except Exception as e:
            log.info("[positions] PositionCore instance error: %s", e)
            continue

    return [], modpath

def _get_items_from_manager(context: Dict[str, Any]) -> List[Any]:
    dl = context.get("dl")
    if not dl:
        return []
    mgr = getattr(dl, "positions", None) or getattr(dl, "dl_positions", None)
    if not mgr:
        return []
    # prefer explicit getters; fall back to attributes
    for name in ("get_all_positions", "get_active_positions", "list", "all"):
        f = getattr(mgr, name, None)
        if callable(f):
            try:
                items = f()
                if isinstance(items, list) and items:
                    return items
            except Exception as e:
                log.info("[positions] positions manager %s() error: %s", name, e)
                # try next
                continue
    arr = getattr(mgr, "items", None) or getattr(mgr, "open", None)
    return arr if isinstance(arr, list) else []

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

    # Fetch from Core first, then DL manager
    core_items, modpath = _get_items_from_core(context)
    source = None
    items: List[Any] = []

    if core_items:
        items = core_items
        source = f"CORE({modpath})"
    else:
        mgr_items = _get_items_from_manager(context)
        if mgr_items:
            items = mgr_items
            source = "DL"

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
