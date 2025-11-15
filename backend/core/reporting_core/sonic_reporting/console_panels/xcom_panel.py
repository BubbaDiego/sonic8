_safe_render(
    "backend.core.reporting_core.sonic_reporting.xcom_panel",
    "render",
    dl,
)
``` :contentReference[oaicite:0]{index=0}

…and that `xcom_panel.py` currently prints exactly what your screenshot shows. :contentReference[oaicite:1]{index=1}

Let’s replace **that** file (`backend/core/reporting_core/sonic_reporting/xcom_panel.py`) with the new design we agreed on: status bar + recent attempts + snooze/cooldown.

Here’s the **full updated file** for Codex to drop in.

---

### File: `backend/core/reporting_core/sonic_reporting/xcom_panel.py`

```python
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, Optional, List
import time

from .console_panels.theming import emit_title_block
from .xcom_extras import (
    xcom_live_status,
    read_snooze_remaining,
    read_voice_cooldown_remaining,
    get_default_voice_cooldown,
)

PANEL_SLUG = "xcom"
PANEL_NAME = "XCom"


# ───────────────────────── receipts + age helpers ──────────────────────────

def _get_receipt(dl: Any, key: str) -> Optional[Dict[str, Any]]:
    sysmgr = getattr(dl, "system", None)
    if not sysmgr or not hasattr(sysmgr, "get_var"):
        return None
    try:
        rec = sysmgr.get_var(key)
    except Exception:
        return None
    return rec if isinstance(rec, dict) else None


def _compute_age_seconds(rec: Dict[str, Any]) -> int:
    try:
        ts = float(rec.get("ts", 0) or 0)
    except Exception:
        return 0
    age = int(time.time() - ts)
    return age if age >= 0 else 0


def _fmt_age(age_s: int) -> str:
    """Compact age string: 5s, 3m, 2h, 2h3m."""
    if age_s <= 0:
        return "0s"
    if age_s < 90:
        return f"{age_s}s"
    if age_s < 5400:
        return f"{age_s // 60}m"
    h = age_s // 3600
    m = (age_s % 3600) // 60
    return f"{h}h" if m == 0 else f"{h}h{m}m"


# ───────────────────────── attempt formatting ──────────────────────────────

def _target_from_rec(rec: Dict[str, Any]) -> str:
    mon = rec.get("monitor") or ""
    lab = rec.get("label") or ""
    if mon or lab:
        return f"{mon}:{lab}".strip(":")
    return "-"


def _format_channels_compact(ch: Dict[str, Any]) -> str:
    """sys✅ voice❌ sms— tts—"""
    def flag(name: str) -> str:
        val = ch.get(name)
        if val is True:
            return "✅"
        if val is False:
            return "❌"
        return "—"

    return (
        f"sys{flag('system')} "
        f"voice{flag('voice')} "
        f"sms{flag('sms')} "
        f"tts{flag('tts')}"
    )


def _result_for_send(rec: Dict[str, Any]) -> str:
    summary = rec.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()

    res = rec.get("result")
    if isinstance(res, dict):
        if res.get("success") is False:
            return "FAIL"
        if res.get("success") is True:
            return "OK"
    return "OK"


def _result_for_skip(rec: Dict[str, Any]) -> str:
    reason = (rec.get("reason") or "-").upper()
    remaining = rec.get("remaining_seconds")
    minimum = rec.get("min_seconds")
    parts: List[str] = [reason]
    if remaining is not None:
        parts.append(f"remaining={int(remaining)}s")
    if minimum is not None:
        parts.append(f"min={int(minimum)}s")
    return " ".join(parts)


def _result_for_error(rec: Dict[str, Any]) -> str:
    reason = (rec.get("reason") or "-").upper()
    missing = rec.get("missing")
    if missing:
        try:
            detail = "missing=" + ", ".join(missing)
        except Exception:
            detail = f"missing={missing}"
    else:
        detail = str(rec.get("detail") or "").strip()
    return f"{reason} {detail}".strip()


def _build_attempt(kind: str, rec: Dict[str, Any]) -> Dict[str, Any]:
    age_s = _compute_age_seconds(rec)
    target = _target_from_rec(rec)

    if kind == "send":
        result = _result_for_send(rec)
        ch_map = rec.get("channels") or {}
        chan = _format_channels_compact(ch_map) if isinstance(ch_map, dict) else "—"
    elif kind == "skip":
        result = _result_for_skip(rec)
        chan = "—"
    else:  # "error"
        result = _result_for_error(rec)
        chan = "—"

    return {
        "type": kind,
        "age_s": age_s,
        "age": _fmt_age(age_s),
        "target": target,
        "result": result,
        "channels": chan,
    }


def _recent_attempts(
    rec_send: Optional[Dict[str, Any]],
    rec_skip: Optional[Dict[str, Any]],
    rec_err: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Build a small list of recent attempts from the last send/skip/error receipts."""
    events: List[Dict[str, Any]] = []
    if rec_send:
        events.append(_build_attempt("send", rec_send))
    if rec_skip:
        events.append(_build_attempt("skip", rec_skip))
    if rec_err:
        events.append(_build_attempt("error", rec_err))
    # Sort by age ascending → newest first
    events.sort(key=lambda e: e["age_s"])
    return events


# ───────────────────────── snooze / cooldown summaries ─────────────────────

def _snooze_summary(dl: Any, rec_skip: Optional[Dict[str, Any]]) -> str:
    remaining = None
    minimum = None

    if isinstance(rec_skip, dict):
        remaining = rec_skip.get("remaining_seconds")
        minimum = rec_skip.get("min_seconds")

    if remaining is None:
        try:
            rem, _ = read_snooze_remaining(dl)
            if rem > 0:
                remaining = rem
        except Exception:
            pass

    if remaining is None and minimum is None:
        return "global snooze: OFF"

    parts: List[str] = ["global snooze:"]
    if remaining is not None:
        parts.append(f"remaining={int(remaining)}s")
    if minimum is not None:
        parts.append(f"min={int(minimum)}s")
    return " ".join(parts)


def _cooldown_summary(dl: Any, cfg: Optional[Dict[str, Any]]) -> str:
    try:
        rem, _ = read_voice_cooldown_remaining(dl)
    except Exception:
        rem = 0

    try:
        default_cd = int(get_default_voice_cooldown(cfg or {}))
    except Exception:
        default_cd = 180

    if rem > 0:
        return f"voice cooldown: ACTIVE (remaining={int(rem)}s / window={default_cd}s)"
    return f"voice cooldown: idle (window={default_cd}s)"


# ───────────────────────── panel entry ─────────────────────────────────────

def render(dl, *_args, **_kw) -> None:
    """
    Simple XCom text panel used by the Sonic console runner.

    Layout:
      1) Status line (live + channels + last attempt/error ages)
      2) Recent attempts table (latest first)
      3) Snooze / cooldown summary
    """
    rec_send = _get_receipt(dl, "xcom_last_sent")
    rec_skip = _get_receipt(dl, "xcom_last_skip")
    rec_err = _get_receipt(dl, "xcom_last_error")

    cfg_obj = getattr(dl, "global_config", None)
    if not isinstance(cfg_obj, dict):
        cfg_obj = {}

    try:
        live_on, live_src = xcom_live_status(dl, cfg=cfg_obj)
    except Exception:
        live_on, live_src = False, "—"

    status_label = "🟢 LIVE" if live_on else "🔴 OFF"

    attempts = _recent_attempts(rec_send, rec_skip, rec_err)
    snooze_line = _snooze_summary(dl, rec_skip)
    cooldown_line = _cooldown_summary(dl, cfg_obj)

    print()
    for ln in emit_title_block(PANEL_SLUG, PANEL_NAME):
        print(ln)
    print()

    # Status bar
    print(f"  🛰 Status: {status_label}  [src={live_src}]")
    if attempts:
        newest = attempts[0]
        last_err = next((a for a in attempts if a["type"] == "error"), None)
        last_attempt_txt = f"{newest['type']} {newest['age']} ago"
        last_error_txt = f"{last_err['age']} ago" if last_err else "none"
        print(f"     last attempt: {last_attempt_txt}   last error: {last_error_txt}")
    else:
        print("     last attempt: none   last error: none")
    print()

    # Recent attempts table
    print("  📡 Recent XCom attempts (latest first)")
    if not attempts:
        print("    (no recent send/skip/error receipts)")
    else:
        header = (
            "    #  ⏱ Age  🧾 Type  🎯 Target               "
            "🧮 Result / Reason                  📢 Channels"
        )
        print(header)
        for idx, ev in enumerate(attempts, 1):
            num = f"{idx:<2}"
            age = f"{ev['age']:<6}"
            typ = f"{ev['type']:<6}"
            target = f"{ev['target'][:22]:<22}"
            result = f"{ev['result'][:30]:<30}"
            chans = ev["channels"]
            print(f"    {num} {age} {typ} {target} {result} {chans}")
    print()

    # Snooze / cooldown block
    print("  🔕 Snooze / cooldown")
    print(f"    {snooze_line}")
    print(f"    {cooldown_line}")
    print()
