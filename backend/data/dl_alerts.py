# -*- coding: utf-8 -*-
"""
Canonical Alerts store (Alerts v2).

- Schema ensured/migrated on first use (adds missing columns, safe indexes).
- Works with either a live sqlite3.Connection (DataLocker.db) or a path-based store.
- Public API (module-level):
    ensure_schema(dl)
    upsert_open(dl, kind, monitor, symbol, value, threshold, side=None, extra=None) -> alert dict
    resolve_open(dl, kind, monitor, symbol, side=None) -> int
    list_open(dl, kind=None, monitor=None, symbol=None) -> [alerts]
    list_all(dl, kind=None, monitor=None, symbol=None, status=None) -> [alerts]
    list_resolved(dl, kind=None, monitor=None, symbol=None) -> [alerts]
    get_by_id(dl, alert_id) -> alert dict|None
    delete_alert(dl, alert_id) -> int
    touch_dispatch(dl, alert_id) -> None
    record_attempt(dl, alert_id, channel, provider, status, http_status=None, error_code=None, error_msg=None) -> attempt dict

- Class API (for DataLocker): DLAlertManager provides wrappers and legacy names like get_all_alerts().
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ===================== helpers =====================

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guess_db_path(dl: Any) -> str:
    """Resolve DB path from a DataLocker-like object or env/canonical defaults."""
    for attr in ("db_path", "mother_db_path", "database_path"):
        p = getattr(dl, attr, None)
        if isinstance(p, str) and Path(p).exists():
            return p
    p = os.environ.get("SONIC_DB_PATH")
    if p and Path(p).exists():
        return p
    here = Path(__file__).resolve()
    for up in [0, 1, 2, 3, 4, 5]:
        root = here.parents[up] if up > 0 else here.parent
        guess = root.joinpath("..", "mother.db").resolve()
        if guess.exists():
            return str(guess)
    return r"C:\sonic7\backend\mother.db"


@contextmanager
def _cx(dl: Any):
    """
    Transaction helper. Accepts either:
      - a live sqlite3.Connection (e.g., DataLocker.db), or
      - a DataLocker-like object from which we can infer a DB path.
    """
    if isinstance(dl, sqlite3.Connection):
        yield dl
        try:
            dl.commit()
        except Exception:
            pass
        return

    db_path = _guess_db_path(dl)
    conn = sqlite3.connect(db_path, timeout=30)
    try:
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    finally:
        conn.close()


def _dicts(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(r) for r in rows or []]


# ===================== DDL & migration =====================

DDL_ALERTS_CREATE = """
CREATE TABLE IF NOT EXISTS alerts (
  id TEXT PRIMARY KEY,
  kind TEXT,
  monitor TEXT,
  symbol TEXT,
  side TEXT,
  value REAL,
  threshold REAL,
  status TEXT,
  occurrences INTEGER DEFAULT 1,
  first_seen_at TEXT,
  last_seen_at TEXT,
  last_dispatch_at TEXT,
  fingerprint TEXT,
  extra TEXT
);
"""

DDL_ALERT_ATTEMPTS_CREATE = """
CREATE TABLE IF NOT EXISTS alert_attempts (
  id TEXT PRIMARY KEY,
  alert_id TEXT NOT NULL,
  ts TEXT NOT NULL,
  channel TEXT NOT NULL,
  provider TEXT NOT NULL,
  status TEXT NOT NULL,
  http_status INTEGER,
  error_code TEXT,
  error_msg TEXT,
  FOREIGN KEY(alert_id) REFERENCES alerts(id)
);
"""

IDX_UNIQ_FINGERPRINT = "CREATE UNIQUE INDEX IF NOT EXISTS ux_alerts_fingerprint ON alerts(fingerprint);"
IDX_STATUS_MONITOR_SYMBOL = "CREATE INDEX IF NOT EXISTS idx_alerts_status_monitor_symbol ON alerts(status, monitor, symbol);"
IDX_ATTEMPTS_ALERT = "CREATE INDEX IF NOT EXISTS idx_attempts_alert ON alert_attempts(alert_id);"


def _columns(cx: sqlite3.Connection, table: str) -> List[str]:
    try:
        cur = cx.execute(f"PRAGMA table_info({table})")
        return [r["name"] for r in cur.fetchall()]
    except Exception:
        return []


def _add_column(cx: sqlite3.Connection, table: str, col: str, decl: str) -> None:
    cx.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def _safe_create_indexes(cx: sqlite3.Connection, cols: List[str]) -> None:
    # unique fingerprint
    if "fingerprint" in cols:
        cx.execute(IDX_UNIQ_FINGERPRINT)
    # status/monitor/symbol composite
    if all(c in cols for c in ("status", "monitor", "symbol")):
        cx.execute(IDX_STATUS_MONITOR_SYMBOL)
    # attempts index
    cx.execute(IDX_ATTEMPTS_ALERT)


def ensure_schema(dl: Any) -> None:
    """
    Idempotent, migration-safe:
      - creates tables if missing
      - adds any missing columns to legacy 'alerts'
      - backfills fingerprint if null
      - creates indexes only if referenced columns exist
    """
    with _cx(dl) as cx:
        cx.executescript(DDL_ALERTS_CREATE)
        cx.executescript(DDL_ALERT_ATTEMPTS_CREATE)

        cols = _columns(cx, "alerts")
        needed: Dict[str, str] = {
            "id": "TEXT",
            "kind": "TEXT",
            "monitor": "TEXT",
            "symbol": "TEXT",
            "side": "TEXT",
            "value": "REAL",
            "threshold": "REAL",
            "status": "TEXT",
            "occurrences": "INTEGER DEFAULT 1",
            "first_seen_at": "TEXT",
            "last_seen_at": "TEXT",
            "last_dispatch_at": "TEXT",
            "fingerprint": "TEXT",
            "extra": "TEXT",
        }
        for name, decl in needed.items():
            if name not in cols:
                _add_column(cx, "alerts", name, decl)

        # backfill minimal fingerprint for rows that lack it
        cols = _columns(cx, "alerts")
        if "fingerprint" in cols and "symbol" in cols:
            cx.execute("""
                UPDATE alerts
                   SET fingerprint = COALESCE(fingerprint, 'breach|' || COALESCE(monitor,'liquid') || '|' || UPPER(symbol))
                 WHERE fingerprint IS NULL AND symbol IS NOT NULL
            """)

        _safe_create_indexes(cx, cols)


# ===================== public API (module-level) =====================

def _fingerprint(kind: str, monitor: str, symbol: str, *, side: Optional[str] = None) -> str:
    fp = f"{kind}|{monitor}|{symbol.upper()}"
    if side:
        fp += f"|{side.lower()}"
    return fp


def upsert_open(
    dl: Any, *,
    kind: str,
    monitor: str,
    symbol: str,
    value: Optional[float],
    threshold: Optional[float],
    side: Optional[str] = None,
    extra: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert or update an OPEN alert (bump occurrences & last_seen_at)."""
    ensure_schema(dl)
    fp = _fingerprint(kind, monitor, symbol, side=side)
    now = _iso_now()
    with _cx(dl) as cx:
        cur = cx.execute("SELECT * FROM alerts WHERE fingerprint=?", (fp,))
        row = cur.fetchone()
        if row:
            cx.execute(
                """UPDATE alerts SET
                       value = COALESCE(?, value),
                       threshold = COALESCE(?, threshold),
                       status = 'open',
                       occurrences = occurrences + 1,
                       last_seen_at = ?,
                       monitor = COALESCE(monitor, ?)
                   WHERE fingerprint=?""",
                (value, threshold, now, monitor, fp),
            )
            cur = cx.execute("SELECT * FROM alerts WHERE fingerprint=?", (fp,))
            return dict(cur.fetchone())
        else:
            aid = str(uuid.uuid4())
            cx.execute(
                """INSERT INTO alerts
                   (id, kind, monitor, symbol, side, value, threshold, status,
                    occurrences, first_seen_at, last_seen_at, last_dispatch_at,
                    fingerprint, extra)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'open', 1, ?, ?, NULL, ?, ?)""",
                (aid, kind, monitor, symbol.upper(), side, value, threshold, now, now, fp, extra),
            )
            cur = cx.execute("SELECT * FROM alerts WHERE id=?", (aid,))
            return dict(cur.fetchone())


def resolve_open(dl: Any, *, kind: str, monitor: str, symbol: str, side: Optional[str] = None) -> int:
    """Resolve any open alert matching the fingerprint. Returns rows updated."""
    ensure_schema(dl)
    fp = _fingerprint(kind, monitor, symbol, side=side)
    now = _iso_now()
    with _cx(dl) as cx:
        cur = cx.execute(
            "UPDATE alerts SET status='resolved', last_seen_at=? WHERE fingerprint=? AND status='open'",
            (now, fp),
        )
        return cur.rowcount


def list_open(dl: Any, *, kind: Optional[str] = None, monitor: Optional[str] = None, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    """List open alerts, optionally filtered."""
    ensure_schema(dl)
    q = "SELECT * FROM alerts WHERE status='open'"
    args: List[Any] = []
    if kind:
        q += " AND kind=?"; args.append(kind)
    if monitor:
        q += " AND monitor=?"; args.append(monitor)
    if symbol:
        q += " AND UPPER(symbol)=?"; args.append(symbol.upper())
    q += " ORDER BY last_seen_at DESC"
    with _cx(dl) as cx:
        cur = cx.execute(q, tuple(args))
        return _dicts(cur.fetchall())


def list_all(
    dl: Any, *,
    kind: Optional[str] = None,
    monitor: Optional[str] = None,
    symbol: Optional[str] = None,
    status: Optional[str] = None,  # 'open' | 'resolved' | None
) -> List[Dict[str, Any]]:
    """List all alerts (open/resolved), with optional filters."""
    ensure_schema(dl)
    q = "SELECT * FROM alerts WHERE 1=1"
    args: List[Any] = []
    if kind:
        q += " AND kind=?"; args.append(kind)
    if monitor:
        q += " AND monitor=?"; args.append(monitor)
    if symbol:
        q += " AND UPPER(symbol)=?"; args.append(symbol.upper())
    if status in ("open", "resolved"):
        q += " AND status=?"; args.append(status)
    q += " ORDER BY last_seen_at DESC"
    with _cx(dl) as cx:
        cur = cx.execute(q, tuple(args))
        return _dicts(cur.fetchall())


def list_resolved(dl: Any, *, kind: Optional[str] = None, monitor: Optional[str] = None, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
    return list_all(dl, kind=kind, monitor=monitor, symbol=symbol, status="resolved")


def get_by_id(dl: Any, alert_id: str) -> Optional[Dict[str, Any]]:
    ensure_schema(dl)
    with _cx(dl) as cx:
        cur = cx.execute("SELECT * FROM alerts WHERE id=?", (alert_id,))
        r = cur.fetchone()
        return dict(r) if r else None


def delete_alert(dl: Any, alert_id: str) -> int:
    """Hard-delete an alert (use judiciously). Returns rows deleted."""
    ensure_schema(dl)
    with _cx(dl) as cx:
        cx.execute("DELETE FROM alert_attempts WHERE alert_id=?", (alert_id,))
        cur = cx.execute("DELETE FROM alerts WHERE id=?", (alert_id,))
        return cur.rowcount


def touch_dispatch(dl: Any, alert_id: str) -> None:
    ensure_schema(dl)
    now = _iso_now()
    with _cx(dl) as cx:
        cx.execute("UPDATE alerts SET last_dispatch_at=? WHERE id=?", (now, alert_id))


def record_attempt(
    dl: Any, *,
    alert_id: str,
    channel: str,
    provider: str,
    status: str,  # 'success'|'fail'|'skipped'
    http_status: Optional[int] = None,
    error_code: Optional[str] = None,
    error_msg: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist a notification attempt and update last_dispatch_at when meaningful."""
    ensure_schema(dl)
    now = _iso_now()
    aid = str(uuid.uuid4())
    with _cx(dl) as cx:
        cx.execute(
            """INSERT INTO alert_attempts
                 (id, alert_id, ts, channel, provider, status, http_status, error_code, error_msg)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (aid, alert_id, now, channel, provider, status, http_status, error_code, error_msg),
        )
        if status in ("success", "fail"):
            cx.execute("UPDATE alerts SET last_dispatch_at=? WHERE id=?", (now, alert_id))
        cur = cx.execute("SELECT * FROM alert_attempts WHERE id=?", (aid,))
        return dict(cur.fetchone())


# ===================== class manager for DataLocker =====================

class DLAlertManager:
    """
    DataLocker-facing wrapper, including legacy-style methods expected by Cyclone.
    Construct with a live sqlite3.Connection (e.g., DataLocker.db) or with DataLocker itself.
    """

    def __init__(self, dl: Any):
        self.dl = dl
        ensure_schema(self.dl)

    def ensure_schema(self) -> None:
        ensure_schema(self.dl)

    # Back-compat / expected by Cyclone
    def get_all_alerts(
        self,
        kind: Optional[str] = None,
        monitor: Optional[str] = None,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return list_all(self.dl, kind=kind, monitor=monitor, symbol=symbol, status=status)

    def get_open_alerts(
        self, kind: Optional[str] = None, monitor: Optional[str] = None, symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return list_open(self.dl, kind=kind, monitor=monitor, symbol=symbol)

    def get_resolved_alerts(
        self, kind: Optional[str] = None, monitor: Optional[str] = None, symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return list_resolved(self.dl, kind=kind, monitor=monitor, symbol=symbol)

    # Canonical wrappers
    def upsert_open(
        self, *, kind: str, monitor: str, symbol: str, value: Optional[float],
        threshold: Optional[float], side: Optional[str] = None, extra: Optional[str] = None
    ) -> Dict[str, Any]:
        return upsert_open(self.dl, kind=kind, monitor=monitor, symbol=symbol,
                           value=value, threshold=threshold, side=side, extra=extra)

    def resolve_open(self, *, kind: str, monitor: str, symbol: str, side: Optional[str] = None) -> int:
        return resolve_open(self.dl, kind=kind, monitor=monitor, symbol=symbol, side=side)

    def get_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        return get_by_id(self.dl, alert_id)

    def delete_alert(self, alert_id: str) -> int:
        return delete_alert(self.dl, alert_id)

    def touch_dispatch(self, alert_id: str) -> None:
        touch_dispatch(self.dl, alert_id)

    def record_attempt(
        self, *, alert_id: str, channel: str, provider: str, status: str,
        http_status: Optional[int] = None, error_code: Optional[str] = None, error_msg: Optional[str] = None
    ) -> Dict[str, Any]:
        return record_attempt(self.dl, alert_id=alert_id, channel=channel, provider=provider,
                              status=status, http_status=ok_int(http_status),
                              error_code=error_code, error_msg=error_msg)


# tiny helper to coerce http_status safely
def ok_int(v: Optional[int]) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except Exception:
        return None
