# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import os
import unicodedata

# ===== colors (title/header text only) =====
USE_COLOR   = os.getenv("SONIC_COLOR", "1").strip().lower() not in {"0","false","no","off"}
TITLE_COLOR = os.getenv("SONIC_TITLE_COLOR", "\x1b[38;5;45m")
HEAD_COLOR  = os.getenv("SONIC_HEAD_COLOR",  "\x1b[38;5;81m")
def _c(s: str, color: str) -> str: return f"{color}{s}\x1b[0m" if USE_COLOR else s

# ===== layout =====
HR_WIDTH = 78
INDENT   = "  "
W_ICON, W_ACTIVITY, W_OUTCOME, W_STATUS, W_ELAPSED = 3, 26, 36, 8, 7

# emoji-safe padding
_VAR={0xFE0F,0xFE0E}; _ZW={0x200D,0x200C}
def _dl(s: str) -> int:
    t=0
    for ch in s or "":
        cp=ord(ch)
        if cp in _VAR or cp in _ZW: continue
        ew=unicodedata.east_asian_width(ch)
        t += 2 if ew in ("W","F") else 1
    return t

def _pad(s: Any, w: int, *, right=False) -> str:
    t = "" if s is None else str(s)
    L = _dl(t)
    if L >= w:
        while t and _dl(t) > w: t = t[:-1]
        return t
    pad = " " * (w - L)
    return (pad + t) if right else (t + pad)

def _pad_center(s: Any, w: int) -> str:
    t = "" if s is None else str(s)
    L = _dl(t)
    if L >= w:
        while t and _dl(t) > w: t = t[:-1]
        return t
    total = w - L
    left = total // 2
    right = total - left
    return (" " * left) + t + (" " * right)

def _hr(title: str) -> str:
    label_text = f"🔁 {title}"
    raw = f" {label_text} "
    pad = HR_WIDTH - len(raw)
    if pad < 0:
        pad = 0
    left = pad // 2
    right = pad - left
    return INDENT + ("─" * left) + " " + _c(label_text, TITLE_COLOR) + " " + ("─" * right)

# ===== util =====
def _secs(ms: Any) -> str:
    try:
        if ms is None: return ""
        return f"{float(ms)/1000:.2f}"
    except: return ""

ICON = {
    "prices": "💵",
    "positions": "📊",
    "raydium": "🪙",
    "hedges": "🪶",
    "profit": "💰",
    "liquid": "💧",
    "market": "📈",
    "reporters": "🧭",
    "heartbeat": "💓",
}
STAT = {"ok":"✅","warn":"⚠️","error":"✖️","skip":"⚪"}

# ===== data =====
def _latest_cycle_id(dl: Any) -> Optional[str]:
    cur = dl.db.get_cursor()
    cur.execute("SELECT MAX(cycle_id) FROM cycle_activities")
    r = cur.fetchone()
    return r[0] if r and r[0] else None

def _rows_for_cycle(dl: Any, cycle_id: str) -> List[Dict[str, Any]]:
    cur = dl.db.get_cursor()
    cur.execute(
        "SELECT phase, label, outcome, notes, duration_ms FROM cycle_activities WHERE cycle_id=? ORDER BY id ASC",
        (cycle_id,),
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]

# ===== render =====
def render(dl, *_unused, default_json_path=None):
    cid = _latest_cycle_id(dl)
    print(_hr("Cycle Activity"))
    if not cid:
        print("  (no activity yet)")
        return
    rows = _rows_for_cycle(dl, cid)

    # colored header text only
    h_activity = _c("Activity", HEAD_COLOR)
    h_outcome  = _c("Outcome", HEAD_COLOR)
    h_status   = _c("Status", HEAD_COLOR)
    h_elapsed  = _c("Elapsed", HEAD_COLOR)

    print(
        "    "
        + _pad("", W_ICON)                              # icon column blank
        + _pad(h_activity, W_ACTIVITY)
        + _pad(h_outcome,  W_OUTCOME)
        + _pad_center(h_status, W_STATUS)
        + _pad_center(h_elapsed, W_ELAPSED)
    )

    for r in rows:
        icon = ICON.get(r["phase"], "⚙️") + " "
        status = STAT.get(str(r.get("outcome") or "ok").lower(), "✅")
        notes = str(r.get("notes") or "")
        seconds = _secs(r.get("duration_ms"))
        print(
            "    "
            + _pad(icon, W_ICON)
            + _pad(str(r.get("label") or r.get("phase")), W_ACTIVITY)
            + _pad(notes, W_OUTCOME)
            + _pad_center(status, W_STATUS)
            + _pad_center(seconds, W_ELAPSED)
        )
