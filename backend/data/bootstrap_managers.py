# -*- coding: utf-8 -*-
from __future__ import annotations
"""
bootstrap_managers.py
- Ensures a 'positions' manager exists on the DataLocker.
- If none is registered, installs a DB-backed fallback manager that reads the 'positions' table.
"""

from typing import Any, List, Mapping, Optional
import sqlite3


# Utilities
def _as_dict(obj: Any) -> Mapping[str, Any]:
    if isinstance(obj, dict):
        return obj
    return getattr(obj, "__dict__", {}) or {}


def _dl_has_positions(dl: Any) -> bool:
    # Check common shapes for an existing 'positions' manager
    gm = getattr(dl, "get_manager", None)
    if callable(gm) and gm("positions"):
        return True
    fn = getattr(dl, "manager", None)
    if callable(fn) and fn("positions"):
        return True
    mgrs = getattr(dl, "managers", None)
    if isinstance(mgrs, dict) and "positions" in mgrs:
        return True
    get = getattr(dl, "get", None)
    if callable(get) and get("positions"):
        return True
    reg = getattr(dl, "registry", None)
    if isinstance(reg, dict) and "positions" in reg:
        return True
    return False


def _get_db_conn(dl: Any) -> Optional[sqlite3.Connection]:
    # Try common DL db access points
    for name in ("get_db", "db", "connect_db"):
        fn = getattr(dl, name, None)
        if callable(fn):
            try:
                conn = fn()
                if isinstance(conn, sqlite3.Connection):
                    return conn
            except Exception:
                continue
    db_attr = getattr(dl, "db", None)
    if isinstance(db_attr, sqlite3.Connection):
        return db_attr
    return None


class DBPositionsManager:
    """
    Minimal manager that returns 'active' positions from the DB.
    Provides .active() to mirror typical manager APIs.
    """

    def __init__(self, dl: Any) -> None:
        self._dl = dl

    def _conn(self) -> Optional[sqlite3.Connection]:
        return _get_db_conn(self._dl)

    def active(self) -> List[Mapping[str, Any]]:
        conn = self._conn()
        if not conn:
            return []
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(positions)")
            cols = {c[1] for c in cur.fetchall()}
            order_col = "updated_at" if "updated_at" in cols else ("created_at" if "created_at" in cols else "rowid")
            cur.execute(
                f"""
                SELECT * FROM positions
                WHERE status IN ('active','OPEN','open') OR status IS NULL
                ORDER BY {order_col} DESC
                LIMIT 200
            """
            )
            names = [d[0] for d in cur.description]
            rows = [dict(zip(names, r)) for r in cur.fetchall()]
            return rows
        except Exception:
            return []
        finally:
            try:
                conn.close()
            except Exception:
                pass


def ensure_default_managers(dl: Any) -> None:
    """
    Idempotent: if a 'positions' manager already exists, do nothing.
    Otherwise register a DB-backed fallback.
    """

    try:
        if _dl_has_positions(dl):
            return

        # Find a registration method
        register = getattr(dl, "register_manager", None)
        if callable(register):
            register("positions", DBPositionsManager(dl))
            return

        # Some DLs expose a dict to stuff managers into
        mgrs = getattr(dl, "managers", None)
        if isinstance(mgrs, dict):
            mgrs["positions"] = DBPositionsManager(dl)
            return

        # Last resort: keep a registry dict
        reg = getattr(dl, "registry", None)
        if isinstance(reg, dict):
            reg["positions"] = DBPositionsManager(dl)
            return

        # If all else fails, try to attach a 'manager' method dynamically (not ideal, but safe)
        if not hasattr(dl, "manager"):
            # no dynamic monkey-patching here; we quietly exit
            pass
    except Exception as e:
        print(f"[DL] bootstrap positions manager failed: {type(e).__name__}: {e}")
