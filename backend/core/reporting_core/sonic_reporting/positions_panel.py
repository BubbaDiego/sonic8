# -*- coding: utf-8 -*-
from __future__ import annotations
"""
positions_panel — DL-sourced positions table (consolidated)

Design goals:
- Pull active positions directly from the DataLocker manager (primary).
- Fall back to last-known rows in SQLite if the manager is empty.
- Normalize rows using the same shape expected by the snapshot printer
  so headers/columns/alignments are IDENTICAL to the snapshot table.
- Print a source breadcrumb, then return to caller.
"""

from typing import Any, Mapping, Optional, Dict, List, Tuple
from pathlib import Path
import sqlite3

# ---- DL import (lazy-safe)
try:
    from backend.data.data_locker import DataLocker  # type: ignore
except Exception:  # pragma: no cover
    DataLocker = None  # type: ignore

# ---- Reuse the snapshot formatter to guarantee identical layout
try:
    # Private helpers are fine inside the same package namespace.
    from backend.core.reporting_core.sonic_reporting.positions_snapshot import _print_positions_table as _print_table  # type: ignore
except Exception:  # pragma: no cover
    _print_table = None  # type: ignore


# ---------- tiny utils ----------
def _as_dict(obj: Any) -> Mapping[str, Any]:
    if isinstance(obj, Mapping):
        return obj
    return getattr(obj, "__dict__", {}) or {}

def _get_any(row: Mapping[str, Any], *names: str) -> Any:
    for n in names:
        if n in row:
            return row.get(n)
    # nested common containers
    for nest in ("risk", "meta", "stats"):
        d = row.get(nest)
        if isinstance(d, Mapping):
            for n in names:
                if n in d:
                    return d.get(n)
    return None

def _as_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None

# ---------- normalization ----------
def _normalize_row(p: Any) -> Dict[str, Any]:
    """
    Produce the dict shape that _print_positions_table expects:
      {asset, side, value, pnl, lev, liq, travel}
    We accept a wider set of field aliases than the snapshot to
    fix missing Asset/Side seen in some DL providers.
    """
    row = _as_dict(p)

    # Asset: include asset_type/base/name fallbacks
    asset = _get_any(row, "asset", "symbol", "ticker", "coin", "name", "asset_type", "base_asset")
    if isinstance(asset, str):
        asset = asset.upper()
    elif asset is None:
        asset = "---"

    # Side: many providers vary; map truthy/booleans too
    side = _get_any(row, "side", "position", "dir", "direction", "position_side", "long_short")
    if side is None:
        # boolean-style flags
        is_long = _get_any(row, "is_long", "long")  # True/False
        if isinstance(is_long, bool):
            side = "LONG" if is_long else "SHORT"
    side = (str(side or "LONG")).upper()
    if side not in ("LONG", "SHORT"):
        side = "LONG"

    # Value/Size/PnL/Lev/Liq/Travel set liberal aliases
    value = _as_float(_get_any(row, "value", "value_usd", "size_usd", "notional", "notional_usd"))
    pnl   = _as_float(_get_any(row, "pnl", "pnl_usd", "pnl_after_fees_usd", "unrealized_pnl", "profit", "pl"))
    lev   = _as_float(_get_any(row, "lev", "leverage", "x"))
    liq   = _as_float(_get_any(row, "liq", "liq_pct", "liquidation", "liquidation_distance", "liquidation_distance_pct", "liq_dist"))
    travel = _as_float(_get_any(row, "travel", "travel_pct", "move_pct", "move", "change_pct", "delta_pct"))

    # Compute travel if missing and we have entry/mark
    if travel is None:
        entry = _as_float(_get_any(row, "entry", "entry_price"))
        mark  = _as_float(_get_any(row, "mark", "mark_price", "price"))
        liq_price = _as_float(_get_any(row, "liq_price", "liquidation_price"))
        if entry and mark:
            if side == "SHORT":
                travel = (entry - mark) / entry * 100.0
                if liq_price is not None and mark >= liq_price:
                    travel = -100.0
            else:
                travel = (mark - entry) / entry * 100.0
                if liq_price is not None and mark <= liq_price:
                    travel = -100.0

    return {
        "asset": asset or "---",
        "side": side,
        "value": value,
        "pnl": pnl,
        "lev": lev,
        "liq": liq,
        "travel": travel,
    }

# ---------- data sources ----------
def _dl() -> Any:
    if DataLocker is None:
        raise RuntimeError("DataLocker module not available")
    try:
        inst = DataLocker.get_instance()
        if inst:
            return inst
    except Exception:
        pass
    # last resort – construct with default env
    return DataLocker()

def _active_positions_via_manager(dl: Any) -> Tuple[List[Mapping[str, Any]], str]:
    try:
        mgr = dl.get_manager("positions")  # standard DL manager
        if not mgr:
            return [], "dl:manager:none"
        rows = mgr.active()  # expected to return sequence of objects/rows
        rows = [ _as_dict(r) for r in rows ] if rows else []
        return rows, "dl:manager.active"
    except Exception:
        return [], "dl:error"

def _last_known_from_db(dl: Any) -> Tuple[List[Mapping[str, Any]], str]:
    conn = None
    try:
        conn = dl.get_db() if hasattr(dl, "get_db") else None
        if not conn:
            return [], "db:none"
        cur = conn.cursor()
        # Try schema-agnostic: prefer created_at if column exists
        cur.execute("PRAGMA table_info(positions)")
        cols = [c[1] for c in cur.fetchall()]
        has_created = "created_at" in cols
        if has_created:
            cur.execute("""
                SELECT *
                FROM positions
                WHERE status IN ('active','OPEN','open') OR status IS NULL
                ORDER BY created_at DESC
                LIMIT 200
            """)
        else:
            cur.execute("""
                SELECT *
                FROM positions
                WHERE status IN ('active','OPEN','open') OR status IS NULL
                ORDER BY rowid DESC
                LIMIT 200
            """)
        colnames = [d[0] for d in cur.description]
        rows = [dict(zip(colnames, r)) for r in cur.fetchall()]
        return rows, "db:fallback"
    except Exception:
        return [], "db:error"
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass

# ---------- public entry ----------
def print_positions_panel(dl: Optional[Any] = None) -> None:
    # Use the DL instance the sequencer gives us, or open our own.
    dl = dl or _dl()

    # 1) Try DL manager (authoritative)
    rows_raw, src = _active_positions_via_manager(dl)
    # 2) Fallback to DB snapshot if empty
    if not rows_raw:
        rows_raw, src = _last_known_from_db(dl)

    # Normalize for the snapshot printer to guarantee identical layout
    rows_norm = [_normalize_row(p) for p in rows_raw]

    # Print table (header, rows, totals) using the shared formatter
    if _print_table is None:
        # defensive fallback: minimal display
        print("Positions")
        for r in rows_norm:
            print(r)
    else:
        _print_table(rows_norm)

    print(f"\n[POSITIONS] {src} ({len(rows_norm)} rows)")

if __name__ == "__main__":
    print_positions_panel()


# Sequencer entrypoint (standard contract: render(dl, csum, default_json_path))
def render(
    dl: Optional[Any] = None,
    csum: Optional[str] = None,
    default_json_path: Optional[Path] = None,
    **_: Any,
) -> None:
    """
    Console sequencer hook.
    Accepts (dl, csum, default_json_path) from the sequencer; only `dl` is used.
    """
    print_positions_panel(dl=dl)
