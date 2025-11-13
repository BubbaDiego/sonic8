# backend/core/reporting_core/sonic_reporting/console_panels/xcom_panel.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
import time

from backend.core.core_constants import XCOM_PROVIDERS_PATH

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

def _get_sys(dl):
    sysmgr = getattr(dl, "system", None)
    return sysmgr if sysmgr and hasattr(sysmgr, "get_var") else None

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

def _dl_provider_snapshot(dl) -> Dict[str, Any]:
    sysmgr = _get_sys(dl)
    pro = sysmgr.get_var("xcom_providers") if sysmgr else None
    v = dict((pro or {}).get("voice") or {})
    sid = v.get("account_sid")
    tok = v.get("auth_token")
    if sid:
        v["account_sid"] = sid[:2] + "…" + sid[-4:] if len(sid) > 6 else "…"
    if tok:
        v["auth_token"] = "…" + tok[-4:] if len(tok) > 4 else "…"
    return {"voice": v or {}, "path": str(XCOM_PROVIDERS_PATH)}

def render(context: Dict[str, Any], width: Optional[int] = None) -> List[str]:
    out: List[str] = []
    body = get_panel_body_config(PANEL_SLUG)
    dl  = context.get("dl")
    cfg = context.get("cfg") or {}
    sysmgr = _get_sys(dl)

    out += emit_title_block(PANEL_SLUG, PANEL_NAME)

    # Providers (from file)
    out += body_indent_lines(PANEL_SLUG, [paint_line("Providers (file)", body["column_header_text_color"])])
    prov = _dl_provider_snapshot(dl)
    v = prov.get("voice", {}) or {}
    out += body_indent_lines(PANEL_SLUG, [
        f"  file: {prov.get('path','-')}",
        f"  voice.enabled={bool(v.get('enabled', True))} provider={v.get('provider','-')}",
        f"  from={v.get('from','-')} to={v.get('to') or []} sid={v.get('account_sid','-')} flow={v.get('flow_sid','-')}",
        "",
    ])

    # Live channels (from cfg)
    out += body_indent_lines(PANEL_SLUG, [paint_line("Live channels (cfg)", body["column_header_text_color"])])
    liq = _live_channels(cfg, "liquid")
    pro = _live_channels(cfg, "profit")
    out += body_indent_lines(PANEL_SLUG, [
        f"  liquid: system={liq['system']} voice={liq['voice']} sms={liq['sms']} tts={liq['tts']}",
        f"  profit: system={pro['system']} voice={pro['voice']} sms={pro['sms']} tts={pro['tts']}",
        "",
    ])

    # Last send
    out += body_indent_lines(PANEL_SLUG, [paint_line("Last send", body["column_header_text_color"])])
    sent = sysmgr.get_var("xcom_last_sent") if sysmgr else None
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
    sk = sysmgr.get_var("xcom_last_skip") if sysmgr else None
    if not sk:
        out += body_indent_lines(PANEL_SLUG, ["  (none)"])
    else:
        age = _fmt_age(sk.get("ts"))
        out += body_indent_lines(PANEL_SLUG, [
            f"  when: {age} ago",
            f"  why : {(sk.get('reason') or '').upper()} (remaining={sk.get('remaining_seconds','-')}s / window={sk.get('min_seconds','-')}s)",
            "",
        ])

    # Last error (provider missing, dispatch exception, etc.)
    out += body_indent_lines(PANEL_SLUG, [paint_line("Last error", body["column_header_text_color"])])
    err = sysmgr.get_var("xcom_last_error") if sysmgr else None
    if not err:
        out += body_indent_lines(PANEL_SLUG, ["  (none)"])
    else:
        age = _fmt_age(err.get("ts"))
        miss = err.get("missing")
        extra = f" (missing: {', '.join(miss)})" if miss else ""
        lines = [
            f"  when: {age} ago",
            f"  what: {err.get('monitor','-')}:{err.get('label','-')}",
            f"  why : {(err.get('reason') or '-').upper()}{extra}",
        ]
        path = err.get("path")
        if path:
            lines.append(f"  file: {path}")
        lines.append("")
        out += body_indent_lines(PANEL_SLUG, lines)

    out += body_pad_below(PANEL_SLUG)
    return out
