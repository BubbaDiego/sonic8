# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime

W_MON, W_LABEL, W_STATE, W_VAL, W_UNIT = 10, 28, 10, 12, 6

def _pad(s: str, n: int, align: str = "left") -> str:
    s = "" if s is None else str(s)
    if len(s) >= n: return s[:n]
    pad = " " * (n - len(s))
    return (s + pad) if align == "left" else (pad + s)

def _fmt_val(v: Any) -> str:
    try:
        f = float(v)
    except Exception:
        return "—"
    sign = "-" if f < 0 else ""
    f = abs(f)
    if f >= 1_000_000: return f"{sign}{f/1_000_000:.1f}m"
    if f >= 1_000:     return f"{sign}{f/1_000:.1f}k"
    return f"{sign}{f:.2f}"

def _latest_status_rows(dl: Any) -> List[Dict[str, Any]]:
    cur = dl.db.get_cursor()
    # pick latest cycle_id
    cur.execute("SELECT MAX(cycle_id) FROM monitor_status")
    row = cur.fetchone()
    if not row or not row[0]:
        return []
    cycle_id = row[0]
    cur.execute("SELECT monitor, label, state, value, unit FROM monitor_status WHERE cycle_id = ? ORDER BY monitor, label", (cycle_id,))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]

def render(dl, *_unused, default_json_path: Optional[str] = None):
    rows = _latest_status_rows(dl)
    print("\n  ---------------------- 🧭  Monitors  ------------------------")
    source = "db.monitor_status"
    print(f"  [MON] source: {source} ({len(rows)} rows)")
    if not rows:
        print("  (no monitor results)")
        return

    header = (
        "    "
        + _pad("Monitor", W_MON)
        + _pad("Label",   W_LABEL)
        + _pad("State",   W_STATE)
        + _pad("Value",   W_VAL, "right")
        + _pad("Unit",    W_UNIT, "right")
    )
    print(header)

    for r in rows:
        print(
            "    "
            + _pad(str(r.get("monitor") or ""), W_MON)
            + _pad(str(r.get("label") or ""),   W_LABEL)
            + _pad(str(r.get("state") or ""),   W_STATE)
            + _pad(_fmt_val(r.get("value")),    W_VAL, "right")
            + _pad(str(r.get("unit") or ""),    W_UNIT, "right")
        )
