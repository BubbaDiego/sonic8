# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, Optional
import time

from .console_panels.theming import emit_title_block

PANEL_SLUG = "xcom"
PANEL_NAME = "XCom"


def _get_receipt(dl: Any, key: str) -> Optional[Dict[str, Any]]:
    sysmgr = getattr(dl, "system", None)
    if not sysmgr or not hasattr(sysmgr, "get_var"):
        return None
    try:
        rec = sysmgr.get_var(key)
    except Exception:
        return None
    return rec if isinstance(rec, dict) else None


def _format_channels(rec: Dict[str, Any]) -> str:
    summary = rec.get("summary")
    if summary:
        return str(summary)
    channels = rec.get("channels") or {}
    parts = []
    for key in ("system", "voice", "sms", "tts"):
        if key in channels:
            parts.append(f"{key}={channels.get(key)}")
    monitor = rec.get("monitor")
    label = rec.get("label")
    prefix = f"{monitor}:{label} " if monitor or label else ""
    return prefix + " ".join(parts)


def _format_skip(rec: Dict[str, Any]) -> str:
    reason = rec.get("reason") or "-"
    remaining = rec.get("remaining_seconds")
    minimum = rec.get("min_seconds")
    monitor = rec.get("monitor")
    label = rec.get("label")
    scope = f"{monitor}:{label} " if monitor or label else ""
    parts = [f"reason={reason}"]
    if remaining is not None:
        parts.append(f"remaining={int(remaining)}s")
    if minimum is not None:
        parts.append(f"min={int(minimum)}s")
    return scope + " ".join(parts)


def _format_error(rec: Dict[str, Any]) -> str:
    reason = rec.get("reason") or "-"
    missing = rec.get("missing")
    monitor = rec.get("monitor")
    label = rec.get("label")
    scope = f"{monitor}:{label} " if monitor or label else ""
    if missing:
        detail = f"missing={missing}"
    else:
        detail = str(rec.get("detail") or "")
    detail = detail.strip()
    return f"{scope}reason={reason}" + (f" {detail}" if detail else "")


def _compute_age_seconds(rec: Dict[str, Any]) -> int:
    try:
        ts = float(rec.get("ts", 0) or 0)
    except Exception:
        return 0
    age = int(time.time() - ts)
    return age if age >= 0 else 0


def render(dl, *_args, **_kw) -> None:
    rec_send = _get_receipt(dl, "xcom_last_sent")
    rec_skip = _get_receipt(dl, "xcom_last_skip")
    rec_err = _get_receipt(dl, "xcom_last_error")

    print()
    for ln in emit_title_block(PANEL_SLUG, PANEL_NAME):
        print(ln)

    print()
    print("     📡 Chan    ⇄ Di 🧾 Type  👤 To/From                 🧮 State   ⏱ Age 🪪 Sourc")
    if not any([rec_send, rec_skip, rec_err]):
        print("  (no xcom messages)")
    else:
        if rec_send:
            age = _compute_age_seconds(rec_send)
            detail = _format_channels(rec_send)
            print(f"  last send:  {detail}   ⏱ {age}s")
        if rec_skip:
            age = _compute_age_seconds(rec_skip)
            detail = _format_skip(rec_skip)
            print(f"  last skip:  {detail}   ⏱ {age}s")
        if rec_err:
            age = _compute_age_seconds(rec_err)
            detail = _format_error(rec_err)
            print(f"  last error: {detail}   ⏱ {age}s")

    print()
