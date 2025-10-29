# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, Optional

def _fetchall(cur):
    try:
        return cur.fetchall() or []
    except Exception:
        return []

def read_positions(dl, cycle_id: Optional[str]) -> Dict[str, Any]:
    """Snapshot first (sonic_positions), fallback to positions. Robust to column name variants."""
    out = {"count": 0, "pnl_single_max": 0.0, "pnl_portfolio_sum": 0.0, "rows": []}
    try:
        cur = dl.db.get_cursor()
        if not cur: return out
        if cycle_id:
            cur.execute("SELECT * FROM sonic_positions WHERE cycle_id = ?", (cycle_id,))
        else:
            cur.execute("SELECT * FROM positions WHERE status='ACTIVE'")
        rows = _fetchall(cur)
        out["count"] = len(rows)
        vals = []
        for r in rows:
            if isinstance(r, dict) or hasattr(r, "keys"):
                pnl = r.get("pnl_after_fees_usd")
                if pnl is None: pnl = r.get("pnl_usd")
                if pnl is None: pnl = r.get("pnl")
            else:
                pnl = r[3] if len(r) > 3 else 0.0
            try:
                vals.append(float(pnl) if pnl is not None else 0.0)
            except Exception:
                vals.append(0.0)
        pos = [v for v in vals if v > 0]
        out["pnl_single_max"]   = max(pos) if pos else 0.0
        out["pnl_portfolio_sum"]= sum(pos) if pos else 0.0
        out["rows"] = rows
    except Exception:
        pass
    return out

def read_hedges(dl, cycle_id: Optional[str]) -> Dict[str, Any]:
    out = {"planned": 0, "active": 0, "errors": 0}
    try:
        cur = dl.db.get_cursor()
        if not cur: return out
        if cycle_id:
            cur.execute("SELECT status, COUNT(1) FROM sonic_hedges WHERE cycle_id=? GROUP BY status", (cycle_id,))
        else:
            cur.execute("SELECT status, COUNT(1) FROM hedges GROUP BY status")
        for status, cnt in _fetchall(cur):
            s = str(status or "").lower()
            if "plan" in s: out["planned"] = int(cnt or 0)
            elif "active" in s: out["active"] = int(cnt or 0)
            elif "err" in s or "fail" in s: out["errors"] = int(cnt or 0)
    except Exception:
        pass
    return out
