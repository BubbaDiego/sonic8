# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# =============== common helpers ===============

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _guess_db_path(dl: Any) -> str:
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
    return r"C:\\sonic7\\backend\\mother.db"

@contextmanager
def _cx(dl: Any):
    """
    Accept either a live sqlite3.Connection (DataLocker often passes this),
    or a DataLocker-like object we can resolve to a db path.
    """
    if isinstance(dl, sqlite3.Connection):
        yield dl
        try: dl.commit()
        except Exception: pass
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


# =============== DDL & migration ===============

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
    if "fingerprint" in cols:
        cx.execute(IDX_UNIQ_FINGERPRINT)
    if all(c in cols for c in ("status", "monitor", "symbol")):
        cx.execute(IDX_STATUS_MONITOR_SYMBOL)
    cx.execute(IDX_ATTEMPTS_ALERT)

def ensure_schema(dl: Any) -> None:
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
        # backfill fingerprint if missing
        cols = _columns(cx, "alerts")
        if "fingerprint" in cols and "symbol" in cols:
            cx.execute("""
                UPDATE alerts
                   SET fingerprint = COALESCE(fingerprint, 'breach|' || COALESCE(monitor,'liquid') || '|' || UPPER(symbol))
                 WHERE fingerprint IS NULL AND symbol IS NOT NULL
            """)
        _safe_create_indexes(cx, cols)


# =============== module-level API ===============

def _fingerprint(kind: str, monitor: str, symbol: str, *, side: Optional[str] = None) -> str:
    s = f"{kind}|{monitor}|{symbol.upper()}"
    if side: s += f"|{side.lower()}"
    return s

def upsert_open(
    dl: Any, *, kind: str, monitor: str, symbol: str,
    value: Optional[float], threshold: Optional[float],
    side: Optional[str] = None, extra: Optional[str] = None
) -> Dict[str, Any]:
    ensure_schema(dl)
    fp = _fingerprint(kind, monitor, symbol, side=side)
    now = _iso_now()
    with _cx(dl) as cx:
        cur = cx.execute("SELECT * FROM alerts WHERE fingerprint=?", (fp,))
        r = cur.fetchone()
        if r:
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
    ensure_schema(dl)
    q = "SELECT * FROM alerts WHERE status='open'"
    args: List[Any] = []
    if kind:    q += " AND kind=?";    args.append(kind)
    if monitor: q += " AND monitor=?"; args.append(monitor)
    if symbol:  q += " AND UPPER(symbol)=?"; args.append(symbol.upper())
    q += " ORDER BY last_seen_at DESC"
    with _cx(dl) as cx:
        cur = cx.execute(q, tuple(args))
        return _dicts(cur.fetchall())

def get_by_id(dl: Any, alert_id: str) -> Optional[Dict[str, Any]]:
    ensure_schema(dl)
    with _cx(dl) as cx:
        cur = cx.execute("SELECT * FROM alerts WHERE id=?", (alert_id,))
        r = cur.fetchone()
        return dict(r) if r else None

def touch_dispatch(dl: Any, alert_id: str) -> None:
    ensure_schema(dl)
    now = _iso_now()
    with _cx(dl) as cx:
        cx.execute("UPDATE alerts SET last_dispatch_at=? WHERE id=?", (now, alert_id))

def record_attempt(
    dl: Any, *, alert_id: str, channel: str, provider: str, status: str,
    http_status: Optional[int] = None, error_code: Optional[str] = None, error_msg: Optional[str] = None,
) -> Dict[str, Any]:
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


# =============== class manager for DataLocker ===============

class DLAlertManager:
    def __init__(self, dl: Any):
        self.dl = dl
        ensure_schema(self.dl)

    def ensure_schema(self) -> None:
        ensure_schema(self.dl)

    def upsert_open(self, **kw) -> Dict[str, Any]:
        return upsert_open(self.dl, **kw)

    def resolve_open(self, **kw) -> int:
        return resolve_open(self.dl, **kw)

    def list_open(self, **kw) -> List[Dict[str, Any]]:
        return list_open(self.dl, **kw)

    def get_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        return get_by_id(self.dl, alert_id)

    def touch_dispatch(self, alert_id: str) -> None:
        touch_dispatch(self.dl, alert_id)

    def record_attempt(self, **kw) -> Dict[str, Any]:
        return record_attempt(self.dl, **kw)
