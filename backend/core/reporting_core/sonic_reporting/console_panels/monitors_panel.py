# backend/core/reporting_core/sonic_reporting/console_panels/monitors_panel.py
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional
import os, time, datetime

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

def _age_from_ts(ts: Any) -> str:
    # ts may be epoch float/int or iso string
    try:
        if isinstance(ts, (int, float)):
            dt = datetime.datetime.utcfromtimestamp(float(ts))
        else:
            dt = datetime.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        secs = max(0, int((datetime.datetime.utcnow() - dt.replace(tzinfo=None)).total_seconds()))
        return f"{secs}s"
    except Exception:
        return "—"

# ---------- hard source: dl.dl_monitors (or dl.monitors) ----------
def _get_monitors_manager(dl: Any):
    for attr in ("dl_monitors", "monitors"):
        if hasattr(dl, attr):
            return getattr(dl, attr)
    return None

def _iter_rows_from_mgr(mgr: Any) -> Iterable[Dict[str, Any]]:
    """
    Strict manager read—NO fallbacks.
    Accepts:
      - method: get_rows()
      - attribute: rows / items
    Each row is expected to be MonitorStatus-like:
      { monitor|mon|label, state, value, unit, thr_op, thr_value, thr_unit, source, ts }
    """
    fn = getattr(mgr, "get_rows", None)
    if callable(fn):
        try:
            got = fn()
            if isinstance(got, list):
                for r in got:
                    if isinstance(r, dict):
                        yield r
                return
        except Exception:
            pass

    for attr in ("rows", "items"):
        arr = getattr(mgr, attr, None)
        if isinstance(arr, list):
            for r in arr:
                if isinstance(r, dict):
                    yield r
            return

def _fmt_thr(op: Any, val: Any, unit: Any) -> str:
    op_s = str(op or "").strip()
    val_s = _nz(val)
    unit_s = str(unit or "").strip()
    if op_s and op_s not in {"=", "=="}:
        s = f"{op_s} {val_s}"
    else:
        s = f"{val_s}"
    return f"{s}{unit_s if unit_s else ''}"

def _fmt_state(s: Any) -> str:
    us = str(s or "").upper()
    if us.startswith("OK"):
        return f"{ICON_OK} {s}"
    if us.startswith("WARN"):
        return f"{ICON_WARN} {s}"
    if us.startswith("ERR") or us.startswith("FAIL") or us.startswith("BREACH"):
        return f"{ICON_ERR} {s}"
    return str(s or "-")

# ---------- render ----------
def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    out: List[str] = []
    try:
        out += emit_title_block(PANEL_SLUG, PANEL_NAME)
        body = get_panel_body_config(PANEL_SLUG)

        dl = context.get("dl")
        mgr = _get_monitors_manager(dl) if dl is not None else None
        if mgr is None:
            out += body_indent_lines(PANEL_SLUG, ["[MONITORS] missing dl.dl_monitors / dl.monitors — fix pipeline"])
            out += body_pad_below(PANEL_SLUG)
            return out

        hdr = f"{'Monitor':<22} {'Thresh':>10}  {'Value':>10}  {'State':>10}  {'Age':>6}  {'Source'}"
        out += body_indent_lines(PANEL_SLUG, [paint_line(hdr, body["column_header_text_color"])])

        any_row = False
        for r in _iter_rows_from_mgr(mgr):
            d = _sd(r)
            mon = _nz(_first(d.get("monitor"), d.get("mon"), d.get("label")))
            thr = _fmt_thr(d.get("thr_op"), d.get("thr_value"), d.get("thr_unit"))
            val = _nz(_first(d.get("value"), d.get("val")))
            unit = _nz(d.get("unit"), "")
            if unit and unit != "-":
                val = f"{val}{unit}"
            st  = _fmt_state(d.get("state"))
            age = _age_from_ts(_first(d.get("age_s"), d.get("ts")))
            src = _nz(_first(d.get("source"), d.get("origin")))
            line = f"{mon:<22} {thr:>10}  {val:>10}  {st:>10}  {age:>6}  {src}"
            out += body_indent_lines(PANEL_SLUG, [color_if_plain(line, body["body_text_color"])])
            any_row = True

        if not any_row:
            out += body_indent_lines(PANEL_SLUG, ["(no monitor checks)"])

        out += body_pad_below(PANEL_SLUG)
        return out
    except Exception as e:
        out.append(f"[REPORT] monitors panel failed: {e}")
        return out
