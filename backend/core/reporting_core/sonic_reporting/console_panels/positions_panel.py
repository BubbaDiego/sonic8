# backend/core/reporting_core/sonic_reporting/console_panels/positions_panel.py
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_below, body_indent_lines,
    paint_line, color_if_plain,
)

PANEL_SLUG = "positions"
PANEL_NAME = "Positions"

# ──────────────────────────────────────────────────────────────────────────────
# Import PositionCore (robustly) and call get_active_positions ONLY
# ──────────────────────────────────────────────────────────────────────────────

def _import_position_core():
    """
    Try common module paths for PositionCore on Sonic branches.
    If none work, raise ImportError with hints.
    """
    candidates = (
        "backend.core.positions_core.position_core",
        "backend.core.position_core",
        "backend.positions.position_core",
        "backend.core.portfolio_core.position_core",
        "backend.core.position.position_core",
    )
    last_err = None
    for mod in candidates:
        try:
            m = __import__(mod, fromlist=["PositionCore"])
            if hasattr(m, "PositionCore"):
                return m.PositionCore
        except Exception as e:
            last_err = e
    raise ImportError(f"PositionCore not found in {candidates}; last error: {last_err}")

def _get_active_positions(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Call PositionCore.get_active_positions.
    We support both instance and classmethod styles:
      - core = PositionCore(dl) ; core.get_active_positions()
      - PositionCore.get_active_positions(dl)
      - core = PositionCore(cfg) ; core.get_active_positions()
      - core = PositionCore() ; core.get_active_positions()
    """
    PositionCore = _import_position_core()
    dl  = context.get("dl")
    cfg = context.get("cfg") or context.get("config")

    # try classmethod style first
    for arg in (dl, cfg, None):
        try:
            if hasattr(PositionCore, "get_active_positions"):
                res = PositionCore.get_active_positions(arg) if arg is not None else PositionCore.get_active_positions()  # type: ignore
                if isinstance(res, list):
                    return res
        except TypeError:
            pass
        except Exception:
            # if the classmethod exists but raises, let instance flow try
            break

    # instance styles
    for arg in (dl, cfg, None):
        try:
            core = PositionCore(arg) if arg is not None else PositionCore()  # type: ignore
            if hasattr(core, "get_active_positions"):
                res = core.get_active_positions()  # type: ignore
                if isinstance(res, list):
                    return res
        except Exception:
            continue

    # no luck → explicit diagnostic
    raise RuntimeError("PositionCore.get_active_positions() is not callable with (dl|cfg|no-arg) on this branch")

# ──────────────────────────────────────────────────────────────────────────────
# Formatting helpers
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

def _sym(d: Dict[str, Any]) -> str:
    return str(_first(d.get("symbol"), d.get("asset"), d.get("sym"), d.get("name"), "—"))

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

def _totals(items: List[Dict[str, Any]]) -> Tuple[str, str, str, str, str, str, str, str]:
    size = value = pnl = 0.0
    n = 0
    levs: List[float] = []
    travs: List[float] = []
    for d in items:
        n += 1
        v = _num(_first(d.get("size"), d.get("sizeUsd")));          size  += 0.0 if v is None else v
        v = _num(_first(d.get("valueUsd"), d.get("value")));        value += 0.0 if v is None else v
        v = _num(_first(d.get("pnlUsd"), d.get("pnl")));            pnl   += 0.0 if v is None else v
        v = _num(_first(d.get("lev"), d.get("leverage")));          levs.append(v) if v is not None else None
        v = _num(_first(d.get("travelPct"), d.get("travel")));      travs.append(v) if v is not None else None
    avg_lev  = sum(levs)/len(levs)   if levs  else None
    avg_trav = sum(travs)/len(travs) if travs else None
    return (
        "Totals",
        _fmt_size(size),
        _fmt_money(value),
        _fmt_money(pnl),
        _fmt_lev(avg_lev),
        "—", "—",
        _fmt_pct(avg_trav),
    )

def _format_totals(items: List[Dict[str, Any]]) -> str:
    t = _totals(items)
    return f"{t[0]:<8} {t[1]:>9} {t[2]:>10} {t[3]:>9} {t[4]:>6} {t[5]:>6} {t[6]:>6} {t[7]:>6}"

# ──────────────────────────────────────────────────────────────────────────────
# Render (PositionCore only; no fallbacks)
# ──────────────────────────────────────────────────────────────────────────────
def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    out: List[str] = []  # always defined
    try:
        out += emit_title_block(PANEL_SLUG, PANEL_NAME)

        body = get_panel_body_config(PANEL_SLUG)
        header = f"{'🪙Asset':<8} {'📦Size':>9} {'🟩Value':>10} {'📈PnL':>9} {'🧷Lev':>6} {'💧Liq':>6} {'🔥Heat':>6} {'🧭Trave':>6}"
        out += body_indent_lines(PANEL_SLUG, [paint_line(header, body["column_header_text_color"])])

        # Strict source: PositionCore.get_active_positions()
        items = _get_active_positions(context)
        if not isinstance(items, list):
            out += body_indent_lines(PANEL_SLUG, ["[POSITIONS] PositionCore.get_active_positions() returned non-list"])
            out += body_pad_below(PANEL_SLUG)
            return out

        if not items:
            out += body_indent_lines(PANEL_SLUG, ["(no positions)"])
            out += body_pad_below(PANEL_SLUG)
            return out

        for d in items:
            if not isinstance(d, dict):
                # try model-like object
                d = getattr(d, "__dict__", {}) or {}
            out += body_indent_lines(PANEL_SLUG, [color_if_plain(_row_from_item(d), body["body_text_color"])])

        out += body_indent_lines(PANEL_SLUG, [paint_line(_format_totals(items), body["totals_row_color"])])
        out += body_pad_below(PANEL_SLUG)
        return out

    except Exception as e:
        out.append(f"[REPORT] positions (PositionCore) failed: {e}")
        return out
