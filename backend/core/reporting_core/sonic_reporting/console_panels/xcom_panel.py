from __future__ import annotations
from typing import Any, Dict, List, Optional
import time

from .theming import (
    emit_title_block,
    get_panel_body_config,
    body_pad_below, body_indent_lines,
    paint_line, color_if_plain,
)

PANEL_SLUG = "xcom"
PANEL_NAME = "XCom"

def _fmt_age(ts: Optional[float]) -> str:
    if not ts: return "—"
    try:
        delta = max(0, int(time.time() - float(ts)))
        if delta < 90: return f"{delta}s"
        if delta < 5400: return f"{delta//60}m"
        return f"{delta//3600}h"
    except Exception:
        return "—"

def _read_sys(dl) -> Dict[str, Any]:
    sysmgr = getattr(dl, "system", None)
    if not sysmgr or not hasattr(sysmgr, "get_var"):
        return {}
    return {
        "sent": sysmgr.get_var("xcom_last_sent"),
        "skip": sysmgr.get_var("xcom_last_skip"),
    }

def _channels_from_cfg(cfg: Dict[str, Any], name: str) -> Dict[str, bool]:
    root1 = (cfg.get(f"{name}_monitor") or {})
    root2 = (cfg.get(name) or {})
    notif = {}
    if isinstance(root1, dict) and "notifications" in root1:
        notif = root1.get("notifications") or {}
    elif isinstance(root2, dict) and "notifications" in root2:
        notif = root2.get("notifications") or {}
    return {
        "system": bool(notif.get("system")),
        "voice":  bool(notif.get("voice")),
        "sms":    bool(notif.get("sms")),
        "tts":    bool(notif.get("tts")),
    }

def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    out: List[str] = []
    body = get_panel_body_config(PANEL_SLUG)

    dl  = context.get("dl")
    cfg = context.get("cfg") or {}

    out += emit_title_block(PANEL_SLUG, PANEL_NAME)

    # Read receipts
    sysvars = _read_sys(dl)
    last_sent = sysvars.get("sent")
    last_skip = sysvars.get("skip")

    # Section: Live channels (liquid/profit) from cfg
    out += body_indent_lines(PANEL_SLUG, [paint_line("Live channels", body["column_header_text_color"])])
    ch_liq = _channels_from_cfg(cfg, "liquid")
    ch_prof= _channels_from_cfg(cfg, "profit")
    out += body_indent_lines(PANEL_SLUG, [
        f"  liquid: system={ch_liq.get('system')} voice={ch_liq.get('voice')} sms={ch_liq.get('sms')} tts={ch_liq.get('tts')}",
        f"  profit: system={ch_prof.get('system')} voice={ch_prof.get('voice')} sms={ch_prof.get('sms')} tts={ch_prof.get('tts')}",
        "",
    ])

    # Section: Last send
    out += body_indent_lines(PANEL_SLUG, [paint_line("Last send", body["column_header_text_color"])])
    if not last_sent:
        out += body_indent_lines(PANEL_SLUG, ["  (none yet)"])
    else:
        age = _fmt_age(last_sent.get("ts"))
        mon = last_sent.get("monitor","")
        label = last_sent.get("label","")
        ch = last_sent.get("channels",{}) or {}
        out += body_indent_lines(PANEL_SLUG, [
            f"  when: {age} ago",
            f"  what: {mon}:{label}",
            f"  chan: system={ch.get('system')} voice={ch.get('voice')} sms={ch.get('sms')} tts={ch.get('tts')}",
            "",
        ])

    # Section: Last skip (why nothing sent)
    out += body_indent_lines(PANEL_SLUG, [paint_line("Last skip", body["column_header_text_color"])])
    if not last_skip:
        out += body_indent_lines(PANEL_SLUG, ["  (none)"])
    else:
        age = _fmt_age(last_skip.get("ts"))
        reason = (last_skip.get("reason") or "").upper()
        rem = last_skip.get("remaining_seconds")
        mins = last_skip.get("min_seconds")
        out += body_indent_lines(PANEL_SLUG, [
            f"  when: {age} ago",
            f"  why : {reason} (remaining={rem}s / window={mins}s)",
        ])

    out += body_pad_below(PANEL_SLUG)
    return out
