# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import os
import unicodedata

# ===== colors (title text only) =====
USE_COLOR   = os.getenv("SONIC_COLOR", "1").strip().lower() not in {"0","false","no","off"}
TITLE_COLOR = os.getenv("SONIC_TITLE_COLOR", "\x1b[38;5;45m")
def _c(s: str, color: str) -> str: return f"{color}{s}\x1b[0m" if USE_COLOR else s

# ===== layout =====
HR_WIDTH = 78
INDENT   = "  "
W_ICON, W_ACTIVITY, W_NOTES, W_STATUS, W_SEC = 2, 26, 44, 8, 8

# emoji safe padding
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
    if L>=w:
        while t and _dl(t)>w: t=t[:-1]
        return t
    pad = " "*(w-L)
    return (pad+t) if right else (t+pad)

def _hr(title: str) -> str:
    # color only text; bars plain
    plain = f"  {title} "
    colored = f" {_c('🔁  ' + title, TITLE_COLOR)} "
    pad = HR_WIDTH - len(plain)
    if pad < 0: pad = 0
    L = pad // 2; R = pad - L
    return INDENT + "─"*L + colored + "─"*R

# ===== table helpers =====
def _secs(ms: Any) -> str:
    try:
        if ms is None: return ""
        return f"{float(ms)/1000:.2f}"
    except: return ""

ICON = {"prices":"💵","positions":"📊","raydium":"🪙","hedges":"🪶","profit":"💰","liquid":"💧","market":"📈","reporters":"🧭","heartbeat":"💓"}
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
    print()
    print(_hr("Cycle Activity"))
    if not cid:
        print("  (no activity yet)")
        return
    rows = _rows_for_cycle(dl, cid)
    print(f"  [ACT] cycle={cid} rows={len(rows)}")

    # header
    print(
        "    "
        + _pad("", W_ICON)
        + _pad("Activity", W_ACTIVITY)
        + _pad("Outcome / Notes", W_NOTES)
        + _pad("Status", W_STATUS)
        + _pad("Exec(s)", W_SEC, right=True)
    )

    for r in rows:
        icon = ICON.get(r["phase"], "⚙️")
        status = STAT.get(str(r.get("outcome") or "ok").lower(), "✅")
        notes = str(r.get("notes") or "")
        seconds = _secs(r.get("duration_ms"))
        print(
            "    "
            + _pad(icon, W_ICON)
            + _pad(str(r.get("label") or r.get("phase")), W_ACTIVITY)
            + _pad(notes, W_NOTES)
            + _pad(status, W_STATUS)
            + _pad(seconds, W_SEC, right=True)
        )
