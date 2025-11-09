from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_below,
    body_indent_lines,
    paint_line,
    color_if_plain,
)

PANEL_SLUG = "monitors"
PANEL_NAME = "Monitors"

ICON_OK   = os.getenv("ICON_OK",   "🟩")
ICON_WARN = os.getenv("ICON_WARN", "🟨")
ICON_ERR  = os.getenv("ICON_ERR",  "🟥")

def _sd(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}

def _nz(x: Any, default: str = "-") -> str:
    if x is None: return default
    s = str(x)
    return s if s != "" else default

def _first(*vals):
    for v in vals:
        if v not in (None, "", [], {}, ()):  # pragma: no cover - trivial guard
            return v
    return None

# ---------- data sources (match legacy panel) ---------------------------------

def _rows_from_context(ctx: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Try the same places the old monitor panel used to read its flat rows:
      ctx['monitor_rows'] / ctx['monitors_table'] / ctx['monitor_table']
      ctx['csum']['monitors_detail'] / ['monitors_items'] / ['monitor_rows'] / ['monitors_table']
      ctx['dl'].* helpers if exposed (get_monitor_rows / get_monitors_table / get_monitor_table)
    """
    # direct on context
    for key in ("monitor_rows", "monitors_table", "monitor_table"):
        val = _sd(ctx).get(key)
        if isinstance(val, list) and (not val or isinstance(val[0], dict)):
            return val

    # csum
    csum = _sd(ctx.get("csum"))
    for key in ("monitors_detail", "monitors_items", "monitor_rows", "monitors_table"):
        val = csum.get(key)
        if isinstance(val, list) and (not val or isinstance(val[0], dict)):
            return val

    # datalocker helpers
    dl = ctx.get("dl")
    if dl:
        for name in ("get_monitor_rows", "get_monitors_table", "get_monitor_table"):
            fn = getattr(dl, name, None)
            if callable(fn):
                try:
                    val = fn()
                    if isinstance(val, list) and (not val or isinstance(val[0], dict)):
                        return val
                except Exception:  # pragma: no cover - defensive fetch
                    pass
    return None

def _normalize(rows: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, str]]:
    """
    Normalize to: mon | thresh | value | state | age | source
    """
    for r in rows:
        d = _sd(r)
        mon    = _nz(_first(d.get("mon"), d.get("name"), d.get("monitor"), d.get("label")))
        thresh = _nz(_first(d.get("thresh"), d.get("threshold")))
        value  = _nz(d.get("value"))
        state0 = _nz(d.get("state"))
        age    = _nz(_first(d.get("age"), d.get("age_s"), d.get("age_str")))
        src    = _nz(_first(d.get("source"), d.get("src"), d.get("origin"), d.get("monitor_key")))

        # decorate state with a glyph but preserve text
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

# ---------- render -------------------------------------------------------------

def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    out: List[str] = []
    try:
        # Title (rounded box width from config; we already set zero title padding)
        out += emit_title_block(PANEL_SLUG, PANEL_NAME)

        body_cfg = get_panel_body_config(PANEL_SLUG)

        # Column header (no horizontal line below)
        header = f"{'Monitor':<22} {'Thresh':>8}  {'Value':>8}  {'State':>10}  {'Age':>6}  {'Source'}"
        out += body_indent_lines(PANEL_SLUG, [paint_line(header, body_cfg["column_header_text_color"])])

        # Rows
        rows = _rows_from_context(context) or []
        printed = False
        for row in _normalize(rows):
            line = f"{row['mon']:<22} {row['thresh']:>8}  {row['value']:>8}  {row['state']:>10}  {row['age']:>6}  {row['source']}"
            out += body_indent_lines(PANEL_SLUG, [color_if_plain(line, body_cfg["body_text_color"])])
            printed = True

        if not printed:
            out += body_indent_lines(PANEL_SLUG, ["(no monitor checks)"])

        # Only spacing **after** the body
        out += body_pad_below(PANEL_SLUG)
        return out
    except Exception as e:  # pragma: no cover - defensive to avoid panel crash
        out.append(f"[REPORT] monitors panel failed: {e}")
        return out
