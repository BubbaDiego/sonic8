# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, Optional


def _fetchall(cur):
    try:
        return cur.fetchall() or []
    except Exception:
        return []


def read_positions(dl, cycle_id: Optional[str]) -> Dict[str, Any]:
    """
    Robust positions fetch:
      1) sonic_positions for this cycle_id
      2) latest sonic_positions (any cycle)
      3) positions (no status filter)
    Normalizes tuples → dicts using cursor.description; tolerant of schema drift.
    """
    out = {"count": 0, "pnl_single_max": 0.0, "pnl_portfolio_sum": 0.0, "rows": []}
    try:
        cur = dl.db.get_cursor()
        if not cur:
            return out

        rows = []
        cols = None

        # 1) snapshot for this cycle
        if cycle_id:
            try:
                cur.execute("SELECT * FROM sonic_positions WHERE cycle_id = ?", (cycle_id,))
                rows = _fetchall(cur)
                cols = [d[0] for d in (cur.description or [])]
            except Exception:
                rows = []

        # 2) latest snapshot (any cycle)
        if not rows:
            try:
                cur.execute("SELECT * FROM sonic_positions ORDER BY ts DESC, rowid DESC LIMIT 50")
                rows = _fetchall(cur)
                cols = [d[0] for d in (cur.description or [])]
            except Exception:
                rows = []

        # 3) runtime table (no status gate)
        if not rows:
            cur.execute("SELECT * FROM positions ORDER BY rowid DESC LIMIT 50")
            rows = _fetchall(cur)
            cols = [d[0] for d in (cur.description or [])]

        # normalize tuples to dicts
        if rows and cols and not (isinstance(rows[0], dict) or hasattr(rows[0], "keys")):
            rows = [{cols[i]: r[i] for i in range(min(len(cols), len(r)))} for r in rows]

        out["count"] = len(rows)

        vals = []
        for r in rows:
            if isinstance(r, dict) or hasattr(r, "keys"):
                pnl = r.get("pnl_after_fees_usd") or r.get("pnl_usd") or r.get("pnl")
            else:
                pnl = r[3] if len(r) > 3 else 0.0
            try:
                vals.append(float(pnl) if pnl is not None else 0.0)
            except Exception:
                vals.append(0.0)

        pos = [v for v in vals if v > 0]
        out["pnl_single_max"] = max(pos) if pos else 0.0
        out["pnl_portfolio_sum"] = sum(pos) if pos else 0.0
        out["rows"] = rows
        return out
    except Exception:
        return out
