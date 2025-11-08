# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import os
import unicodedata

# ===== colors (text only; rules/bars stay plain) =====
USE_COLOR   = os.getenv("SONIC_COLOR", "1").strip().lower() not in {"0", "false", "no", "off"}
TITLE_COLOR = os.getenv("SONIC_TITLE_COLOR", "\x1b[38;5;45m")   # cyan/teal
HEAD_COLOR  = os.getenv("SONIC_HEAD_COLOR",  "\x1b[38;5;81m")   # bright blue/teal for column headers

def _c(s: str, color: str) -> str:
    return f"{color}{s}\x1b[0m" if USE_COLOR else s

# ===== layout (house width) =====
HR_WIDTH = 78
INDENT   = "  "

# Slimmer column widths (sum ≈ 78; no extra separators)
W_ICON    = 3   # emoji + space
W_ACTIVITY= 22
W_NOTES   = 36
W_STATUS  = 8
W_SEC     = 7

# ===== emoji-safe padding =====
_VAR = {0xFE0F, 0xFE0E}
_ZW  = {0x200D, 0x200C}

def _disp_len(s: str) -> int:
    tot = 0
    for ch in s:
        cp = ord(ch)
        if cp in _VAR or cp in _ZW:
            continue
        ew = unicodedata.east_asian_width(ch)
        tot += 2 if ew in ("W", "F") else 1
    return tot

def _padw(text: Any, width: int, *, right: bool = False) -> str:
    s = "" if text is None else str(text)
    cur = _disp_len(s)
    if cur >= width:
        # trim to fit
        while s and _disp_len(s) > width:
            s = s[:-1]
        return s
    pad = " " * (width - cur)
    return (pad + s) if right else (s + pad)

def _pad(s: Any, w: int, right: bool = False) -> str:
    return _padw(s, w, right=right)

def _pad_center(s: Any, w: int) -> str:
    t = "" if s is None else str(s)
    cur = _disp_len(t)
    if cur >= w:
        while t and _disp_len(t) > w:
            t = t[:-1]
        return t
    total_pad = w - cur
    left = total_pad // 2
    right = total_pad - left
    return (" " * left) + t + (" " * right)

# ===== title rule =====
def _hr(title: str) -> str:
    # color only the title text, keep bars plain
    plain_for_width = f"  {title} "
    colored = f" {_c('🔁  ' + title, TITLE_COLOR)} "
    pad = HR_WIDTH - len(plain_for_width)
    if pad < 0:
        pad = 0
    L = pad // 2
    R = pad - L
    return INDENT + "─" * L + colored + "─" * R

# ===== util =====
def _secs(ms: Any) -> str:
    try:
        if ms is None:
            return ""
        return f"{float(ms) / 1000:.2f}"
    except Exception:
        return ""

ICON = {
    "prices":    "💵",
    "positions": "📊",
    "raydium":   "🪙",
    "hedges":    "🪶",
    "profit":    "💰",
    "liquid":    "💧",
    "market":    "📈",
    "reporters": "🧭",
    "heartbeat": "💓",
}
STAT = {"ok": "✅", "warn": "⚠️", "error": "✖️", "skip": "⚪"}

# ===== data =====
def _latest_cycle_id(dl: Any) -> Optional[str]:
    cur = dl.db.get_cursor()
    cur.execute("SELECT MAX(cycle_id) FROM cycle_activities")
    r = cur.fetchone()
    return r[0] if r and r[0] else None

def _rows_for_cycle(dl: Any, cycle_id: str) -> List[Dict[str, Any]]:
    cur = dl.db.get_cursor()
    cur.execute(
        "SELECT phase, label, outcome, notes, duration_ms "
        "FROM cycle_activities WHERE cycle_id=? ORDER BY id ASC",
        (cycle_id,),
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]

# ===== render =====
def render(dl, *_unused, default_json_path=None):
    cid = _latest_cycle_id(dl)
    print()
    print(_hr("Cycle Activity"))
    if not cid:
        print("  (no activity yet)")
        return
    rows = _rows_for_cycle(dl, cid)
    print(f"  [ACT] cycle={cid} rows={len(rows)}")

    # colored header text only; emoji-safe padding; centered right columns
    h_activity = _c("Activity", TITLE_COLOR)
    h_notes    = _c("Outcome / Notes", TITLE_COLOR)
    h_status   = _c("Status", TITLE_COLOR)
    h_exec     = _c("Exec(s)", TITLE_COLOR)

    print(
        "    "
        + _pad("", W_ICON)                              # icon column header intentionally blank
        + _pad(h_activity, W_ACTIVITY)
        + _pad(h_notes,    W_NOTES)
        + _pad_center(h_status, W_STATUS)
        + _pad_center(h_exec,   W_SEC)
    )

    for r in rows:
        icon = ICON.get(r["phase"], "⚙️") + " "        # give icon its own cell + a space
        status = STAT.get(str(r.get("outcome") or "ok").lower(), "✅")
        notes  = str(r.get("notes") or "")
        secs   = _secs(r.get("duration_ms"))

        print(
            "    "
            + _pad(icon, W_ICON)                        # dedicated icon cell
            + _pad(str(r.get("label") or r.get("phase")), W_ACTIVITY)
            + _pad(notes, W_NOTES)
            + _pad_center(status, W_STATUS)            # centered Status
            + _pad_center(secs,   W_SEC)               # centered Exec(s)
        )
