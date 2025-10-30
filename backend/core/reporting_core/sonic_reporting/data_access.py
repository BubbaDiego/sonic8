# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, Optional, List, Tuple

# ─────────────────────────────────────────────────────────────
# Low-level helpers
# ─────────────────────────────────────────────────────────────
def _fetchall(cur):
    try:
        return cur.fetchall() or []
    except Exception:
        return []

def _columns(cur) -> List[str]:
    try:
        return [d[0] for d in (cur.description or [])]
    except Exception:
        return []

def _table_exists(cur, name: str) -> bool:
    try:
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (name,))
        return bool(cur.fetchone())
    except Exception:
        return False

def _first_table_with(cur, required: List[str]) -> Optional[str]:
    """Find any table that has ALL required columns."""
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        names = [r[0] for r in _fetchall(cur)]
    except Exception:
        return None
    for t in names:
        try:
            cur.execute(f"PRAGMA table_info({t})")
            cols = {r[1] for r in _fetchall(cur)}
            if all(c in cols for c in required):
                return t
        except Exception:
            continue
    return None

def _rows_as_dicts(rows, cols):
    if rows and cols and not (isinstance(rows[0], dict) or hasattr(rows[0], "keys")):
        return [{cols[i]: r[i] for i in range(min(len(cols), len(r)))} for r in rows]
    return rows

def _read_any_positions(cur, cycle_id: Optional[str]) -> Tuple[List[dict], List[str]]:
    """
    Snapshot-first; then latest snapshot; then runtime positions; finally a heuristic table.
    Normalizes tuple rows to dicts using cursor.description.
    """
    # 1) sonic_positions for this cycle
    if _table_exists(cur, "sonic_positions") and cycle_id:
        cur.execute("SELECT * FROM sonic_positions WHERE cycle_id = ?", (cycle_id,))
        rows = _fetchall(cur); cols = _columns(cur)
        if rows:
            return _rows_as_dicts(rows, cols), cols

    # 2) latest snapshots (by ts; fallback rowid)
    if _table_exists(cur, "sonic_positions"):
        try:
            cur.execute("SELECT * FROM sonic_positions ORDER BY ts DESC, rowid DESC LIMIT 50")
        except Exception:
            cur.execute("SELECT * FROM sonic_positions ORDER BY rowid DESC LIMIT 50")
        rows = _fetchall(cur); cols = _columns(cur)
        if rows:
            return _rows_as_dicts(rows, cols), cols

    # 3) runtime table (no status gate)
    if _table_exists(cur, "positions"):
        cur.execute("SELECT * FROM positions ORDER BY rowid DESC LIMIT 50")
        rows = _fetchall(cur); cols = _columns(cur)
        if rows:
            return _rows_as_dicts(rows, cols), cols

    # 4) heuristic: any table with common “asset” key
    t = _first_table_with(cur, ["asset"]) or _first_table_with(cur, ["asset_type"])
    if t:
        try:
            cur.execute(f"SELECT * FROM {t} ORDER BY rowid DESC LIMIT 50")
            rows = _fetchall(cur); cols = _columns(cur)
            if rows:
                return _rows_as_dicts(rows, cols), cols
        except Exception:
            pass

    return [], []

# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────
def read_positions_db(dl, cycle_id: Optional[str]) -> Dict[str, Any]:
    """
    Return a canonical dict:
      {
        "count": int,
        "pnl_single_max": float,
        "pnl_portfolio_sum": float,
        "rows": [ {asset, side, size_usd, pnl, liq_dist, ...}, ... ]
      }
    Snapshot → latest snapshot → runtime positions; tolerant of schema drift.
    """
    out = {"count": 0, "pnl_single_max": 0.0, "pnl_portfolio_sum": 0.0, "rows": []}
    try:
        cur = dl.db.get_cursor()
        if not cur:
            return out

        rows, cols = _read_any_positions(cur, cycle_id)
        out["count"] = len(rows)

        # compute positive PnL stats
        vals: List[float] = []
        for r in rows:
            pnl = None
            if isinstance(r, dict) or hasattr(r, "keys"):
                pnl = r.get("pnl_after_fees_usd") or r.get("pnl_usd") or r.get("pnl")
            else:
                pnl = r[3] if len(r) > 3 else 0.0
            try:
                vals.append(float(pnl) if pnl is not None else 0.0)
            except Exception:
                vals.append(0.0)

        pos = [v for v in vals if v > 0]
        out["pnl_single_max"]    = max(pos) if pos else 0.0
        out["pnl_portfolio_sum"] = sum(pos) if pos else 0.0
        out["rows"] = rows
        return out
    except Exception:
        return out

# Back-compat alias — many modules import `read_positions`
def read_positions(dl, cycle_id: Optional[str]) -> Dict[str, Any]:
    """Alias to read_positions_db for legacy callers."""
    return read_positions_db(dl, cycle_id)
