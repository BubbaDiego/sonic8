# -*- coding: utf-8 -*-
"""
PositionMonitor — instrumented positions collector & snapshot writer (self-contained).

What this does:
- Locates a positions provider on the DataLocker (e.g., positions_core_adapter).
- Calls a supported method (prefers list_* over get_*), with clear fallback order.
- Normalizes results (model objects → dicts), maps common fields.
- Writes the per-cycle snapshot rows into `sonic_positions` directly (no external DAL).
- Returns a summary dict so the loop can surface adapter issues in the console:
    ret = PositionMonitor.write(ctx)
    summary["positions_error"]    = ret.get("error")
    summary["positions_count"]    = ret.get("count", 0)
    summary["positions_provider"] = ret.get("provider")
    summary["positions_source"]   = ret.get("source")
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
import traceback

# Type-only import to avoid runtime ModuleNotFoundError if your CycleCtx lives elsewhere.
if TYPE_CHECKING:
    try:
        from backend.core.monitor_core.base import CycleCtx  # preferred
    except Exception:  # pragma: no cover
        CycleCtx = Any  # type: ignore[misc]
else:
    CycleCtx = Any  # runtime-safe


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def _now_iso() -> str:
    import datetime as _dt
    return _dt.datetime.utcnow().isoformat()


def _provider_from_dl(dl: Any) -> Any:
    """
    Try common attributes on the DataLocker to find a positions provider.
    Extend this list if your provider lives under a different name.
    """
    for attr in (
        "positions_core_adapter",
        "positions_core",
        "positions",     # thin facade in some repos
        "market",        # last resort: market may proxy positions
    ):
        p = getattr(dl, attr, None)
        if p:
            return p
    return None


def _map_obj(obj: Any) -> Dict[str, Any]:
    """Convert model objects to dicts, tolerating pydantic/dataclasses/custom."""
    if isinstance(obj, dict):
        return obj
    for m in ("model_dump", "dict", "to_dict", "__json__"):
        fn = getattr(obj, m, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                pass
    d = getattr(obj, "__dict__", None)
    return dict(d) if isinstance(d, dict) else {}


def _get_conn(ctx: "CycleCtx"):
    """
    Obtain a sqlite3.Connection from ctx or ctx.dl.
    Tries:
      - ctx.conn
      - ctx.dl.db.get_connection()
      - ctx.dl.db.conn
      - ctx.dl.db.get_cursor().connection
    """
    c = getattr(ctx, "conn", None)
    if c:
        return c
    dl = getattr(ctx, "dl", None)
    if dl:
        db = getattr(dl, "db", None)
        if db:
            if hasattr(db, "get_connection"):
                try:
                    return db.get_connection()
                except Exception:
                    pass
            if hasattr(db, "conn"):
                try:
                    return db.conn
                except Exception:
                    pass
            if hasattr(db, "get_cursor"):
                try:
                    cur = db.get_cursor()
                    conn = getattr(cur, "connection", None)
                    if conn:
                        return conn
                except Exception:
                    pass
    raise RuntimeError("PositionMonitor: no database connection available on ctx/dl")


def _ensure_snapshot_schema(conn) -> None:
    """
    Create `sonic_positions` table if missing (minimal schema for snapshot rendering).
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sonic_positions (
            id              TEXT,
            cycle_id        TEXT,
            asset           TEXT,
            side            TEXT,
            size_usd        REAL,
            entry_price     REAL,
            avg_price       REAL,
            liq_dist        REAL,
            pnl             REAL,
            ts              TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sonic_positions_cycle ON sonic_positions(cycle_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sonic_positions_asset ON sonic_positions(asset)")


def _write_snapshot(conn, cycle_id: str, rows: List[Dict[str, Any]]) -> None:
    """
    Insert snapshot rows. Replaces existing rows for the same (cycle_id, asset, side, id) if any.
    """
    _ensure_snapshot_schema(conn)
    # best-effort cleanup of same-cycle duplicates (optional)
    # conn.execute("DELETE FROM sonic_positions WHERE cycle_id = ?", (cycle_id,))
    payload = []
    for r in rows:
        payload.append(
            (
                r.get("id"),
                cycle_id,
                r.get("asset"),
                r.get("side"),
                r.get("size_usd"),
                r.get("entry_price"),
                r.get("avg_price"),
                r.get("liq_dist"),
                r.get("pnl"),
                r.get("ts"),
            )
        )
    conn.executemany(
        """
        INSERT INTO sonic_positions
            (id, cycle_id, asset, side, size_usd, entry_price, avg_price, liq_dist, pnl, ts)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        payload,
    )
    conn.commit()


def _collect_positions(ctx: "CycleCtx") -> Tuple[List[Dict[str, Any]], Optional[str], str, str]:
    """
    Returns: (rows, error, provider_name, source_method)
    - rows: list of normalized dicts
    - error: None if ok; a short string if provider absent, returned 0 rows, or crashed
    - provider_name: class name discovered on DL
    - source_method: method name used (e.g., list_positions_sync)
    """
    prov = _provider_from_dl(ctx.dl)
    if not prov:
        return [], "no positions provider found on DataLocker", "None", "None"

    prov_name = getattr(prov, "__class__", type("X", (), {})).__name__

    # Choose best available method (batch/list preferred)
    method_order = (
        "list_positions_sync",
        "list_positions",
        "get_positions",
        "get_all_positions",
    )
    source = "None"
    fn = None
    for name in method_order:
        cand = getattr(prov, name, None)
        if callable(cand):
            fn = cand
            source = name
            break

    if not fn:
        return [], f"provider {prov_name} has no list/get methods", prov_name, "None"

    try:
        result = fn()
        raw_rows: List[Any] = list(result or [])
        rows: List[Dict[str, Any]] = [_map_obj(p) for p in raw_rows]

        # Normalize and map to snapshot fields
        ts = _now_iso()
        out: List[Dict[str, Any]] = []
        for p in rows:
            sym = (p.get("asset") or p.get("asset_type") or p.get("symbol") or "").upper()
            side = (p.get("side") or p.get("position_type") or p.get("dir") or "").upper()
            out.append(
                {
                    "id": p.get("id") or p.get("position_id") or p.get("pos_id"),
                    "asset": sym,
                    "side": side,
                    "size_usd": (
                        p.get("size_usd")
                        or p.get("value_usd")
                        or p.get("position_value_usd")
                        or p.get("value")
                    ),
                    "entry_price": p.get("entry_price") or p.get("avg_entry") or p.get("avg_price"),
                    "avg_price": p.get("avg_price"),
                    "liq_dist": (
                        p.get("liq_dist")
                        or p.get("liquidation_distance")
                        or p.get("liq_percent")
                    ),
                    "pnl": (
                        p.get("pnl_after_fees_usd")
                        or p.get("pnl_usd")
                        or p.get("pnl")
                    ),
                    "ts": ts,
                }
            )

        if not out:
            return [], f"provider {prov_name}.{source} returned 0 rows", prov_name, source

        return out, None, prov_name, source

    except Exception as e:
        tb = traceback.format_exc(limit=2)
        return [], f"provider {prov_name}.{source} crashed: {type(e).__name__}: {e} | {tb.splitlines()[-1]}", prov_name, source


# ─────────────────────────────────────────────────────────────
# Public API expected by MonitorCore
# ─────────────────────────────────────────────────────────────
class PositionMonitor:
    """
    Class form expected by MonitorCore: PositionMonitor.write(ctx) -> dict
    """

    @staticmethod
    def write(ctx: "CycleCtx") -> Dict[str, Any]:
        """
        Collect positions, write snapshot rows when present, return a summary:
          { 'count': int, 'error': str|None, 'provider': str, 'source': str }
        The caller (loop) should stash 'error' in the cycle summary so the console
        can print it inline with the prices tape.
        """
        rows, err, provider, source = _collect_positions(ctx)
        try:
            if rows:
                conn = _get_conn(ctx)
                _write_snapshot(conn, ctx.cycle_id, rows)
        except Exception as e:
            # escalate write errors distinctly
            err = err or f"snapshot write failed: {type(e).__name__}: {e}"
        return {"count": len(rows), "error": err, "provider": provider, "source": source}
