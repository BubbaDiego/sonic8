# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import os
import re
import unicodedata

# ===== standardized title via console_panels.theming =====
from .console_panels.theming import (
    console_width as _theme_width,
    hr as _theme_hr,
    title_lines as _theme_title,
    want_outer_hr,
)
PANEL_SLUG = "activity"
PANEL_NAME = "Cycle Activity"

# ===== colors (title/header text only; bars remain plain) =====
USE_COLOR   = os.getenv("SONIC_COLOR", "1").strip().lower() not in {"0","false","no","off"}
TITLE_COLOR = os.getenv("SONIC_TITLE_COLOR", "\x1b[38;5;45m")  # cyan for title text
HEAD_COLOR  = os.getenv("SONIC_HEAD_COLOR",  "\x1b[38;5;81m")  # teal/blue for header text only

def _c(s: str, color: str) -> str:
    return f"{color}{s}\x1b[0m" if USE_COLOR else s

# ===== layout (78-col house width) =====
HR_WIDTH = 78
INDENT   = "  "

# icon + 4 tight data columns
W_ICON     = 3     # emoji + one space
W_ACTIVITY = 26
W_OUTCOME  = 36
W_STATUS   = 8
W_ELAPSED  = 7

# ===== ANSI & emoji-safe padding =====
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")  # strip ANSI SGR sequences
_VAR = {0xFE0F, 0xFE0E}                   # variation selectors
_ZW  = {0x200D, 0x200C}                   # zero-width joiners

def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)

def _disp_len(s: str) -> int:
    """Visible cell width: ANSI stripped; W/F wide chars count as 2; ignore ZW/VS."""
    s_plain = _strip_ansi(s)
    total = 0
    for ch in s_plain:
        cp = ord(ch)
        if cp in _VAR or cp in _ZW:
            continue
        ew = unicodedata.east_asian_width(ch)
        total += 2 if ew in ("W", "F") else 1
    return total

def _pad(s: Any, w: int, *, right: bool = False) -> str:
    t = "" if s is None else str(s)
    L = _disp_len(t)
    if L >= w:
        while t and _disp_len(t) > w:
            t = t[:-1]
        return t
    pad = " " * (w - L)
    return (pad + t) if right else (t + pad)

def _pad_center(s: Any, w: int) -> str:
    t = "" if s is None else str(s)
    L = _disp_len(t)
    if L >= w:
        while t and _disp_len(t) > w:
            t = t[:-1]
        return t
    total = w - L
    left  = total // 2
    right = total - left
    return (" " * left) + t + (" " * right)

# ===== util =====
def _secs(ms: Any) -> str:
    try:
        if ms is None:
            return ""
        return f"{float(ms) / 1000:.2f}"
    except Exception:
        return ""

def _canon_phase(p: str) -> str:
    """prices service → prices; profit monitor → profit; take first token after stripping suffixes."""
    s = (p or "").strip().lower()
    for suf in (" service", " monitor"):
        if s.endswith(suf):
            s = s[: -len(suf)]
            break
    # fallback to first token if still multi-word
    return s.split()[0] if s else s

# icons & status tokens (prices explicitly uses 💵)
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
    width = _theme_width()
    wrap = want_outer_hr(PANEL_SLUG, default_string=PANEL_NAME)
    print()
    if wrap:
        print(_theme_hr(width))
    for ln in _theme_title(PANEL_SLUG, PANEL_NAME, width=width):
        print(ln)
    if wrap:
        print(_theme_hr(width))
    if not cid:
        print("  (no activity yet)")
        return

    rows = _rows_for_cycle(dl, cid)

    # Header exactly as requested; header text colored (bars plain)
    print(
        "    "
        + _pad("", W_ICON)
        + _pad(_c("Activity", HEAD_COLOR), W_ACTIVITY)
        + _pad(_c("Outcome",  HEAD_COLOR), W_OUTCOME)
        + _pad_center(_c("Status",  HEAD_COLOR),  W_STATUS)
        + _pad_center(_c("Elapsed", HEAD_COLOR),  W_ELAPSED)
    )
    # keep visual consistency with other panels
    print(INDENT + "─" * HR_WIDTH)

    for r in rows:
        phase   = _canon_phase((r.get("phase") or ""))
        icon    = ICON.get(phase, "⚙️") + " "            # dedicated icon cell + trailing space
        label   = str(r.get("label") or r.get("phase"))
        outcome = str(r.get("notes") or "")
        status  = STAT.get(str(r.get("outcome") or "ok").lower(), "✅")
        elapsed = _secs(r.get("duration_ms"))

        print(
            "    "
            + _pad(icon, W_ICON)                          # icon column
            + _pad(label,   W_ACTIVITY)
            + _pad(outcome, W_OUTCOME)
            + _pad_center(status,  W_STATUS)             # centered Status
            + _pad_center(elapsed, W_ELAPSED)            # centered Elapsed
        )
