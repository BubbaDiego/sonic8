# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional

# widths
W_ICON, W_ACTIVITY, W_NOTES, W_STATUS, W_SEC = 2, 26, 44, 8, 8

_ICON = {
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

_STATUS = {"ok": "✅", "warn": "⚠️", "error": "✖️", "skip": "⚪"}

def _pad(s: str, n: int, align: str = "left") -> str:
    s = "" if s is None else str(s)
    if len(s) >= n: return s[:n]
    pad = " " * (n - len(s))
    return (s + pad) if align == "left" else (pad + s)

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

def _secs(ms: Any) -> str:
    try:
        if ms is None: return ""
        return f"{float(ms)/1000:.2f}"
    except Exception:
        return ""

def render(dl, *_unused, default_json_path=None):
    cid = _latest_cycle_id(dl)
    print("\n  ---------------------- 🔁  Cycle Activity  -------------------")
    if not cid:
        print("  (no activity yet)")
        return
    rows = _rows_for_cycle(dl, cid)
    print(f"  [ACT] cycle={cid} rows={len(rows)}")

    # Header
    print("    "
          + _pad("", W_ICON)
          + _pad("Activity", W_ACTIVITY)
          + _pad("Outcome / Notes", W_NOTES)
          + _pad("Status", W_STATUS)
          + _pad("Exec(s)", W_SEC, "right"))

    for r in rows:
        icon = _ICON.get(r["phase"], "⚙️")
        status = _STATUS.get(str(r.get("outcome") or "ok"), "✅")
        notes = str(r.get("notes") or "")
        seconds = _secs(r.get("duration_ms"))

        print(
            "    "
            + _pad(icon, W_ICON)
            + _pad(str(r.get("label") or r.get("phase")), W_ACTIVITY)
            + _pad(notes, W_NOTES)
            + _pad(status, W_STATUS)
            + _pad(seconds, W_SEC, "right")
        )
