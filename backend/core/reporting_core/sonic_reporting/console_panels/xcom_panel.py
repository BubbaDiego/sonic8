from __future__ import annotations
from typing import Any, Dict, List, Optional
import time

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_below, body_indent_lines,
    paint_line,
)

PANEL_SLUG = "xcom"
PANEL_NAME = "XCom"

def _fmt_age(ts: Optional[float]) -> str:
    if not ts: return "—"
    try:
        d = max(0, int(time.time() - float(ts)))
        if d < 90:   return f"{d}s"
        if d < 5400: return f"{d//60}m"
        return f"{d//3600}h"
    except Exception:
        return "—"

def _read_var(dl, key: str):
    sysmgr = getattr(dl, "system", None)
    if not sysmgr or not hasattr(sysmgr, "get_var"): return None
    return sysmgr.get_var(key)

def _live_channels(cfg: Dict[str, Any], name: str) -> Dict[str, bool]:
    root1 = cfg.get(f"{name}_monitor") or {}
    root2 = cfg.get(name) or {}
    if isinstance(root1, dict) and "notifications" in root1:
        src = root1.get("notifications") or {}
    elif isinstance(root2, dict) and "notifications" in root2:
        src = root2.get("notifications") or {}
    else:
        src = {}
    return {
        "system": bool(src.get("system")),
        "voice":  bool(src.get("voice")),
        "sms":    bool(src.get("sms")),
        "tts":    bool(src.get("tts")),
    }

def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    out: List[str] = []
    body = get_panel_body_config(PANEL_SLUG)

    dl  = context.get("dl")
    cfg = context.get("cfg") or {}

    out += emit_title_block(PANEL_SLUG, PANEL_NAME)

    # Live channels
    out += body_indent_lines(PANEL_SLUG, [paint_line("Live channels", body["column_header_text_color"])])
    liq = _live_channels(cfg, "liquid")
    pro = _live_channels(cfg, "profit")
    out += body_indent_lines(PANEL_SLUG, [
        f"  liquid: system={liq['system']} voice={liq['voice']} sms={liq['sms']} tts={liq['tts']}",
        f"  profit: system={pro['system']} voice={pro['voice']} sms={pro['sms']} tts={pro['tts']}",
        "",
    ])

    # Last send
    out += body_indent_lines(PANEL_SLUG, [paint_line("Last send", body["column_header_text_color"])])
    sent = _read_var(dl, "xcom_last_sent")
    if not sent:
        out += body_indent_lines(PANEL_SLUG, ["  (none)"])
    else:
        age = _fmt_age(sent.get("ts"))
        mon = sent.get("monitor","")
        lab = sent.get("label","")
        ch  = sent.get("channels",{}) or {}
        out += body_indent_lines(PANEL_SLUG, [
            f"  when: {age} ago",
            f"  what: {mon}:{lab}",
            f"  chan: system={ch.get('system')} voice={ch.get('voice')} sms={ch.get('sms')} tts={ch.get('tts')}",
            "",
        ])

    # Last skip (e.g., global snooze)
    out += body_indent_lines(PANEL_SLUG, [paint_line("Last skip", body["column_header_text_color"])])
    skip = _read_var(dl, "xcom_last_skip")
    if not skip:
        out += body_indent_lines(PANEL_SLUG, ["  (none)"])
    else:
        age = _fmt_age(skip.get("ts"))
        reason = (skip.get("reason") or "").upper()
        remaining = skip.get("remaining_seconds")
        window    = skip.get("min_seconds")
        out += body_indent_lines(PANEL_SLUG, [
            f"  when: {age} ago",
            f"  why : {reason} (remaining={remaining}s / window={window}s)",
        ])

    # Errors section (provider missing, dispatch exception, etc.)
    err = None
    sysmgr = getattr(dl, "system", None)
    if sysmgr and hasattr(sysmgr, "get_var"):
        err = sysmgr.get_var("xcom_last_error")

    out += body_indent_lines(PANEL_SLUG, [""])
    out += body_indent_lines(PANEL_SLUG, [paint_line("Last error", body["column_header_text_color"])])
    if not err:
        out += body_indent_lines(PANEL_SLUG, ["  (none)"])
    else:
        mon = err.get("monitor","-")
        lab = err.get("label","-")
        reason = err.get("reason","-")
        missing = err.get("missing")
        rem = f" (missing: {', '.join(missing)})" if missing else ""
        out += body_indent_lines(PANEL_SLUG, [f"  {mon}:{lab} — {reason}{rem}"])

    out += body_pad_below(PANEL_SLUG)
    return out
