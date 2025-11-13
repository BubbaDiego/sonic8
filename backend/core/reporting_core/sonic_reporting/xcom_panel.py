# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, Optional
import time

from .console_panels.theming import emit_title_block

PANEL_SLUG = "xcom"
PANEL_NAME = "XCom"


def _get_receipt(dl: Any) -> Optional[Dict[str, Any]]:
    sysmgr = getattr(dl, "system", None)
    if not sysmgr or not hasattr(sysmgr, "get_var"):
        return None
    try:
        rec = sysmgr.get_var("xcom_last_sent")
    except Exception:
        return None
    return rec if isinstance(rec, dict) else None


def _format_summary(rec: Dict[str, Any]) -> str:
    summary = rec.get("summary")
    if summary:
        return str(summary)
    channels = rec.get("channels") or {}
    parts = []
    for key in ("system", "voice", "sms", "tts"):
        parts.append(f"{key}={channels.get(key)}")
    return " ".join(parts)


def _compute_age_seconds(rec: Dict[str, Any]) -> int:
    try:
        ts = float(rec.get("ts", 0) or 0)
    except Exception:
        return 0
    age = int(time.time() - ts)
    return age if age >= 0 else 0


def render(dl, *_args, **_kw) -> None:
    rec = _get_receipt(dl)

    print()
    for ln in emit_title_block(PANEL_SLUG, PANEL_NAME):
        print(ln)

    print()
    print("     📡 Chan    ⇄ Di 🧾 Type  👤 To/From                 🧮 State   ⏱ Age 🪪 Sourc")
    if not rec:
        print("  (no xcom messages)")
    else:
        age = _compute_age_seconds(rec)
        detail = _format_summary(rec)
        print(f"  sent: {detail}   ⏱ {age}s")

    print()
