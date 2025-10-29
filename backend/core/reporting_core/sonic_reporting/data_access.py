# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, Optional, List

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

def read_positions_db(dl, cycle_id: Optional[str]) -> Dict[str, Any]:
    """
    DB/snapshot-only reader: sonic_positions (this cycle → latest) → positions → last-resort table.
    Returns normalized rows + basic stats.
    """
    out = {"count": 0, "pnl_single_max": 0.0, "pnl_portfolio_sum": 0.0, "rows": []}
    try:
        cur = dl.db.get_cursor()
        if not cur:
            return out

        rows = []
        # snapshot for this cycle
        if _table_exists(cur, "sonic_positions") and cycle_id:
            cur.execute("SELECT * FROM sonic_positions WHERE cycle_id = ?", (cycle_id,))
            rows = _rows_as_dicts(_fetchall(cur), _columns(cur))

        # latest snapshot
        if not rows and _table_exists(cur, "sonic_positions"):
            try:
                cur.execute("SELECT * FROM sonic_positions ORDER BY ts DESC, rowid DESC LIMIT 50")
            except Exception:
                cur.execute("SELECT * FROM sonic_positions ORDER BY rowid DESC LIMIT 50")
            rows = _rows_as_dicts(_fetchall(cur), _columns(cur))

        # runtime positions (no status filter)
        if not rows and _table_exists(cur, "positions"):
            cur.execute("SELECT * FROM positions ORDER BY rowid DESC LIMIT 50")
            rows = _rows_as_dicts(_fetchall(cur), _columns(cur))

        # last resort: any table with an 'asset' column
        if not rows:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            names = [r[0] for r in _fetchall(cur)]
            for t in names:
                try:
                    cur.execute(f"PRAGMA table_info({t})")
                    cset = {r[1] for r in _fetchall(cur)}
                    if {"asset"} <= cset or {"asset_type"} <= cset:
                        cur.execute(f"SELECT * FROM {t} ORDER BY rowid DESC LIMIT 50")
                        rows = _rows_as_dicts(_fetchall(cur), _columns(cur))
                        if rows:
                            break
                except Exception:
                    continue

        rows = [_normalize_row(r) for r in rows]

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
    except Exception:
        return out
