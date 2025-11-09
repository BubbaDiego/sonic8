from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional
import os

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_below, body_indent_lines,
    paint_line, color_if_plain,
)

PANEL_SLUG = "monitors"
PANEL_NAME = "Monitors"

ICON_OK   = os.getenv("ICON_OK",   "🟩")
ICON_WARN = os.getenv("ICON_WARN", "🟨")
ICON_ERR  = os.getenv("ICON_ERR",  "🟥")

def _sd(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}

def _first(*vals):
    for v in vals:
        if v not in (None, "", [], {}, ()):
            return v
    return None

def _nz(v: Any, dash: str = "-") -> str:
    if v in (None, ""):
        return dash
    return str(v)

# ---- primary: dl_monitors (or aliases) ---------------------------------------

def _rows_from_dl_monitors(ctx: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    dl = ctx.get("dl")
    if not dl:
        return None
    mgr = None
    for attr in ("dl_monitors", "monitors", "monitor_manager", "dl_monitor"):
        if hasattr(dl, attr):
            mgr = getattr(dl, attr)
            break
    if mgr:
        # common method names
        got = None
        for name in ("get_rows", "get_monitor_rows", "rows", "list", "all", "items"):
            fn = getattr(mgr, name, None)
            if callable(fn):
                try:
                    got = fn()
                    break
                except Exception:
                    pass
            elif isinstance(getattr(mgr, name, None), list):
                got = getattr(mgr, name)
                break
        if isinstance(got, list) and (not got or isinstance(got[0], dict)):
            return got

    # dl-level helpers
    for name in ("get_monitor_rows", "get_monitors_table", "get_monitor_table"):
        fn = getattr(dl, name, None)
        if callable(fn):
            try:
                got = fn()
                if isinstance(got, list) and (not got or isinstance(got[0], dict)):
                    return got
            except Exception:
                pass
    return None

# ---- fallbacks (if dl not ready) ---------------------------------------------

def _rows_from_ctx(ctx: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    for key in ("monitor_rows", "monitors_table", "monitor_table"):
        val = _sd(ctx).get(key)
        if isinstance(val, list) and (not val or isinstance(val[0], dict)):
            return val
    return None

def _rows_from_csum(ctx: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    # only as a last resort
    csum = _sd(ctx.get("csum"))
    for key in ("monitors_detail", "monitors_items", "monitor_rows", "monitors_table"):
        val = csum.get(key)
        if isinstance(val, list) and (not val or isinstance(val[0], dict)):
            return val
    return None

# ---- normalize to legacy columns ---------------------------------------------

def _normalize(rows: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, str]]:
    for r in rows:
        d = _sd(r)
        mon    = _nz(_first(d.get("mon"), d.get("name"), d.get("monitor"), d.get("label")))
        thresh = _nz(_first(d.get("thresh"), d.get("threshold")))
        value  = _nz(d.get("value"))
        state0 = _nz(d.get("state"))
        age    = _nz(_first(d.get("age"), d.get("age_s"), d.get("age_str")))
        src    = _nz(_first(d.get("source"), d.get("src"), d.get("origin"), d.get("monitor_key")))
        u = state0.upper()
        if u.startswith("OK"):
            state = f"{ICON_OK} {state0}"
        elif u.startswith("WARN"):
            state = f"{ICON_WARN} {state0}"
        elif u.startswith("ERR") or u.startswith("FAIL"):
            state = f"{ICON_ERR} {state0}"
        else:
            state = state0 or "-"
        yield {"mon": mon, "thresh": thresh, "value": value, "state": state, "age": age, "source": src}

# ---- render ------------------------------------------------------------------

def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    out: List[str] = []
    try:
        out += emit_title_block(PANEL_SLUG, PANEL_NAME)

        body = get_panel_body_config(PANEL_SLUG)
        hdr  = f"{'Monitor':<22} {'Thresh':>8}  {'Value':>8}  {'State':>10}  {'Age':>6}  {'Source'}"
        out += body_indent_lines(PANEL_SLUG, [paint_line(hdr, body["column_header_text_color"])])

        rows = (
            _rows_from_dl_monitors(context)
            or _rows_from_ctx(context)
            or _rows_from_csum(context)
            or []
        )

        if not rows:
            out += body_indent_lines(PANEL_SLUG, ["(no monitor checks)"])
            out += body_pad_below(PANEL_SLUG)
            return out

        for r in _normalize(rows):
            line = f"{r['mon']:<22} {r['thresh']:>8}  {r['value']:>8}  {r['state']:>10}  {r['age']:>6}  {r['source']}"
            out += body_indent_lines(PANEL_SLUG, [color_if_plain(line, body["body_text_color"])])

        out += body_pad_below(PANEL_SLUG)
        return out
    except Exception as e:
        out.append(f"[REPORT] monitors panel failed: {e}")
        return out
