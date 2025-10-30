# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, Optional, Tuple
from .writer import write_line

def _find_provider(dl) -> Any:
    for attr in ("positions_core_adapter", "positions_core", "positions", "market"):
        p = getattr(dl, attr, None)
        if p:
            return p
    return None

def _best_method(prov) -> str:
    for name in ("list_positions_sync", "list_positions", "get_positions", "get_all_positions"):
        if callable(getattr(prov, name, None)):
            return name
    return "—"

def _table_exists(cur, name: str) -> bool:
    try:
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (name,))
        return bool(cur.fetchone())
    except Exception:
        return False

def _count_sonic_positions(cur, cycle_id: Optional[str]) -> Optional[int]:
    """
    Count snapshot rows, preferring:
      1) exact cycle_id
      2) latest ts batch (all rows whose ts == MAX(ts))
      3) total count
    """
    try:
        if not _table_exists(cur, "sonic_positions"):
            return None

        # 1) exact cycle
        if cycle_id:
            cur.execute("SELECT COUNT(1) FROM sonic_positions WHERE cycle_id = ?", (cycle_id,))
            r = cur.fetchone()
            if r and r[0] is not None and int(r[0]) > 0:
                return int(r[0])

        # 2) latest snapshot by ts
        cur.execute("SELECT MAX(ts) FROM sonic_positions")
        r = cur.fetchone()
        max_ts = r[0] if r else None
        if max_ts:
            cur.execute("SELECT COUNT(1) FROM sonic_positions WHERE ts = ?", (max_ts,))
            r2 = cur.fetchone()
            if r2 and r2[0] is not None and int(r2[0]) > 0:
                return int(r2[0])

        # 3) any rows
        cur.execute("SELECT COUNT(1) FROM sonic_positions")
        r3 = cur.fetchone()
        return int(r3[0]) if r3 and r3[0] is not None else None
    except Exception:
        return None

def _count_positions_runtime(cur) -> Optional[int]:
    try:
        if not _table_exists(cur, "positions"):
            return None
        cur.execute("SELECT COUNT(1) FROM positions")
        r = cur.fetchone()
        return int(r[0]) if r and r[0] is not None else None
    except Exception:
        return None

def _resolve_count(dl, csum: Dict[str, Any]) -> Optional[int]:
    # 0) summary hint from adapter (if the loop set it)
    if "positions_count" in csum:
        try:
            return int(csum["positions_count"])
        except Exception:
            pass

    # 1–3) DB fallback
    try:
        cur = dl.db.get_cursor()
        if not cur:
            return None
        cnt = _count_sonic_positions(cur, csum.get("cycle_id"))
        if cnt is not None:
            return cnt
        return _count_positions_runtime(cur)
    except Exception:
        return None

def render(dl, csum: Dict[str, Any]) -> None:
    """
    Always-visible positions debug:
      🔍 Positions Debug : provider <name> • method <source> • rows <count> • status OK|ERR [<err>]
    """
    prov = _find_provider(dl)
    provider = prov.__class__.__name__ if prov else "—"
    source = _best_method(prov) if prov else "—"
    count = _resolve_count(dl, csum)
    err = csum.get("positions_error")

    status = "OK" if not err else "ERR"
    cnt = "unknown" if count is None else str(count)
    extra = "" if not err else f" [{err}]"
    write_line(f"🔍 Positions Debug : provider {provider} • method {source} • rows {cnt} • status {status}{extra}")
