# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, Optional, List, Tuple
from .positions_core_adapter import get_positions_from_core

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

def _normalize_row(r: Any) -> Dict[str, Any]:
    if isinstance(r, dict) or hasattr(r, "keys"):
        asset = r.get("asset") or r.get("asset_type") or r.get("symbol")
        side  = r.get("side") or r.get("position_type") or r.get("dir")
        val   = r.get("size_usd") or r.get("value_usd") or r.get("position_value_usd") or r.get("value")
        pnl   = r.get("pnl_after_fees_usd") or r.get("pnl_usd") or r.get("pnl")
        lev   = r.get("leverage") or r.get("lev") or r.get("leverage_x")
        liq   = r.get("liq_dist") or r.get("liquidation_distance") or r.get("liq_percent") or r.get("liq_distance")
        trav  = r.get("travel_percent") or r.get("movement_percent") or r.get("travel")
        ts    = r.get("ts") or r.get("timestamp") or r.get("time")
        return {
            "asset": asset, "side": side,
            "value_usd": val, "pnl_after_fees_usd": pnl,
            "leverage": lev, "liquidation_distance": liq,
            "travel_percent": trav, "ts": ts
        }
    try:
        asset, side, val, pnl, lev, liq, trav, ts = (list(r) + [None]*8)[:8]
    except Exception:
        asset = side = val = pnl = lev = liq = trav = ts = None
    return {
        "asset": asset, "side": side,
        "value_usd": val, "pnl_after_fees_usd": pnl,
        "leverage": lev, "liquidation_distance": liq,
        "travel_percent": trav, "ts": ts
    }

def _read_any_positions(cur, cycle_id: Optional[str]) -> List[dict]:
    # 1) snapshot for this cycle
    if _table_exists(cur, "sonic_positions") and cycle_id:
        cur.execute("SELECT * FROM sonic_positions WHERE cycle_id = ?", (cycle_id,))
        rows = _rows_as_dicts(_fetchall(cur), _columns(cur))
        if rows: return rows
    # 2) latest snapshots (any cycle)
    if _table_exists(cur, "sonic_positions"):
        try:
            cur.execute("SELECT * FROM sonic_positions ORDER BY ts DESC, rowid DESC LIMIT 50")
        except Exception:
            cur.execute("SELECT * FROM sonic_positions ORDER BY rowid DESC LIMIT 50")
        rows = _rows_as_dicts(_fetchall(cur), _columns(cur))
        if rows: return rows
    # 3) runtime positions (no status gate)
    if _table_exists(cur, "positions"):
        cur.execute("SELECT * FROM positions ORDER BY rowid DESC LIMIT 50")
        rows = _rows_as_dicts(_fetchall(cur), _columns(cur))
        if rows: return rows
    # 4) last resort: any table that looks like positions
    candidate = _first_table_with(cur, ["asset"]) or _first_table_with(cur, ["asset_type"])
    if candidate:
        cur.execute(f"SELECT * FROM {candidate} ORDER BY rowid DESC LIMIT 50")
        rows = _rows_as_dicts(_fetchall(cur), _columns(cur))
        if rows: return rows
    return []

def read_positions(dl, cycle_id: Optional[str], *, csum: Optional[dict] = None) -> Dict[str, Any]:
    """
    Source order:
      A) Positions Core feed (normalized)
      B) csum['positions']['rows'] (runtime summary)
      C) sonic_positions (this cycle → latest)
      D) positions (no status filter), or any table that looks like positions.
    """
    out = {"count": 0, "pnl_single_max": 0.0, "pnl_portfolio_sum": 0.0, "rows": []}

    # A) Positions Core feed
    core_rows = get_positions_from_core(cycle_id)
    if core_rows:
        rows = core_rows
    else:
        # B) From cycle summary
        rows = []
        if isinstance(csum, dict):
            rows_csum = (csum.get("positions") or {}).get("rows") or []
            if rows_csum:
                rows = [_normalize_row(r) for r in rows_csum]

        # C/D) DB lookups if still empty
        if not rows:
            try:
                cur = dl.db.get_cursor()
                if cur:
                    rows = [_normalize_row(r) for r in _read_any_positions(cur, cycle_id)]
            except Exception:
                rows = []

    # Compute stats
    vals: List[float] = []
    for r in rows:
        try:
            v = r.get("pnl_after_fees_usd") or r.get("pnl_usd") or r.get("pnl")
            vals.append(float(v) if v is not None else 0.0)
        except Exception:
            vals.append(0.0)
    pos = [v for v in vals if v > 0]
    out["pnl_single_max"]    = max(pos) if pos else 0.0
    out["pnl_portfolio_sum"] = sum(pos) if pos else 0.0

    out["count"] = len(rows)
    out["rows"]  = rows
    return out
