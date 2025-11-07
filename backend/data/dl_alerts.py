# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ===================== common helpers =====================

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _guess_db_path(dl: Any) -> str:
    """
    Try to find the mother.db path consistently with how the rest of Sonic resolves it.
    """
    # 1) DataLocker-attached paths
    for attr in ("db_path", "mother_db_path", "database_path"):
        p = getattr(dl, attr, None)
        if isinstance(p, str) and Path(p).exists():
            return p
    # 2) Env override
    p = os.environ.get("SONIC_DB_PATH")
    if p and Path(p).exists():
        return p
    # 3) Canonical fallback: backend/mother.db (relative), then Windows dev path
    here = Path(__file__).resolve()
    for up in [0, 1, 2, 3, 4, 5]:
        root = here.parents[up] if up > 0 else here.parent
        guess = root.joinpath("..", "mother.db").resolve()
        if guess.exists():
            return str(guess)
    return r"C:\\sonic7\\backend\\mother.db"

@contextmanager
def _conn_ctx(db_path: str):
    conn = sqlite3.connect(db_path, timeout=30)
    try:
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    finally:
        conn.close()

def _dicts(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(r) for r in rows or []]


# ===================== schema =====================

DDL_ALERTS = """
CREATE TABLE IF NOT EXISTS alerts (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,            -- 'breach' (extensible)
  monitor TEXT NOT NULL,         -- 'liquid', 'profit', etc.
  symbol TEXT NOT NULL,          -- 'SOL', 'BTC', ...
  side TEXT,                     -- 'long'|'short'|NULL
  value REAL,                    -- e.g., distance for 'breach'
  threshold REAL,
  status TEXT NOT NULL,          -- 'open'|'resolved'
  occurrences INTEGER NOT NULL DEFAULT 1,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  last_dispatch_at TEXT,
  fingerprint TEXT NOT NULL UNIQUE,  -- e.g., 'breach|liquid|SOL'
  extra TEXT
);
"""

DDL_ALERT_ATTEMPTS = """
CREATE TABLE IF NOT EXISTS alert_attempts (
  id TEXT PRIMARY KEY,
  alert_id TEXT NOT NULL,
  ts TEXT NOT NULL,
  channel TEXT NOT NULL,         -- 'voice'|'sms'|'tts'|'system'
  provider TEXT NOT NULL,        -- 'twilio'|'textbelt'|...
  status TEXT NOT NULL,          -- 'success'|'fail'|'skipped'
  http_status INTEGER,
  error_code TEXT,
  error_msg TEXT,
  FOREIGN KEY(alert_id) REFERENCES alerts(id)
);
"""

DDL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_alerts_status_monitor_symbol ON alerts(status, monitor, symbol);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_last_seen ON alerts(last_seen_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_attempts_alert ON alert_attempts(alert_id);",
]


# ===================== module-level API (canonical) =====================

def ensure_schema(dl: Any) -> None:
    db_path = _guess_db_path(dl)
    with _conn_ctx(db_path) as cx:
        cx.executescript(DDL_ALERTS)
        cx.executescript(DDL_ALERT_ATTEMPTS)
        for ddl in DDL_INDEXES:
            cx.execute(ddl)

def _fingerprint(kind: str, monitor: str, symbol: str, *, side: Optional[str] = None) -> str:
    s = f"{kind}|{monitor}|{symbol.upper()}"
    if side:
        s += f"|{side.lower()}"
    return s

def upsert_open(
    dl: Any,
    *,
    kind: str,
    monitor: str,
    symbol: str,
    value: Optional[float],
    threshold: Optional[float],
    side: Optional[str] = None,
    extra: Optional[str] = None
) -> Dict[str, Any]:
    """
    Insert or update an OPEN alert (occurrences++, last_seen_at=now).
    Returns the alert row.
    """
    ensure_schema(dl)
    db_path = _guess_db_path(dl)
    fp = _fingerprint(kind, monitor, symbol, side=side)
    now = _iso_now()
    with _conn_ctx(db_path) as cx:
        cur = cx.execute("SELECT * FROM alerts WHERE fingerprint=?", (fp,))
        row = cur.fetchone()
        if row:
            cx.execute(
                """UPDATE alerts SET
                       value = COALESCE(?, value),
                       threshold = COALESCE(?, threshold),
                       status = 'open',
                       occurrences = occurrences + 1,
                       last_seen_at = ?
                   WHERE fingerprint=?""",
                (value, threshold, now, fp),
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

def resolve_open(
    dl: Any,
    *,
    kind: str,
    monitor: str,
    symbol: str,
    side: Optional[str] = None
) -> int:
    """
    Resolve any OPEN alerts matching the fingerprint.
    Returns rows updated.
    """
    ensure_schema(dl)
    db_path = _guess_db_path(dl)
    fp = _fingerprint(kind, monitor, symbol, side=side)
    now = _iso_now()
    with _conn_ctx(db_path) as cx:
        cur = cx.execute(
            "UPDATE alerts SET status='resolved', last_seen_at=? WHERE fingerprint=? AND status='open'",
            (now, fp),
        )
        return cur.rowcount

def list_open(
    dl: Any,
    *,
    kind: Optional[str] = None,
    monitor: Optional[str] = None,
    symbol: Optional[str] = None
) -> List[Dict[str, Any]]:
    ensure_schema(dl)
    db_path = _guess_db_path(dl)
    q = "SELECT * FROM alerts WHERE status='open'"
    args: List[Any] = []
    if kind:
        q += " AND kind=?"; args.append(kind)
    if monitor:
        q += " AND monitor=?"; args.append(monitor)
    if symbol:
        q += " AND UPPER(symbol)=?"; args.append(symbol.upper())
    q += " ORDER BY last_seen_at DESC"
    with _conn_ctx(db_path) as cx:
        cur = cx.execute(q, tuple(args))
        return _dicts(cur.fetchall())

def get_by_id(dl: Any, alert_id: str) -> Optional[Dict[str, Any]]:
    ensure_schema(dl)
    db_path = _guess_db_path(dl)
    with _conn_ctx(db_path) as cx:
        cur = cx.execute("SELECT * FROM alerts WHERE id=?", (alert_id,))
        r = cur.fetchone()
        return dict(r) if r else None

def touch_dispatch(dl: Any, alert_id: str) -> None:
    ensure_schema(dl)
    db_path = _guess_db_path(dl)
    now = _iso_now()
    with _conn_ctx(db_path) as cx:
        cx.execute("UPDATE alerts SET last_dispatch_at=? WHERE id=?", (now, alert_id))

def record_attempt(
    dl: Any,
    *,
    alert_id: str,
    channel: str,
    provider: str,
    status: str,
    http_status: Optional[int] = None,
    error_code: Optional[str] = None,
    error_msg: Optional[str] = None,
) -> Dict[str, Any]:
    ensure_schema(dl)
    db_path = _guess_db_path(dl)
    now = _iso_now()
    aid = str(uuid.uuid4())
    with _conn_ctx(db_path) as cx:
        cx.execute(
            """INSERT INTO alert_attempts
               (id, alert_id, ts, channel, provider, status, http_status, error_code, error_msg)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (aid, alert_id, now, channel, provider, status, http_status, error_code, error_msg),
        )
        # reflect last_dispatch_at for success/fail
        if status in ("success", "fail"):
            cx.execute("UPDATE alerts SET last_dispatch_at=? WHERE id=?", (now, alert_id))
        cur = cx.execute("SELECT * FROM alert_attempts WHERE id=?", (aid,))
        return dict(cur.fetchone())


# ===================== class-based manager (for DataLocker import) =====================

class DLAlertManager:
    """
    Class wrapper that mirrors the module-level API.
    DataLocker can import and instantiate this as it does for other managers.
    """
    def __init__(self, dl: Any):
        self.dl = dl
        ensure_schema(self.dl)

    def ensure_schema(self) -> None:
        ensure_schema(self.dl)

    def upsert_open(
        self,
        *,
        kind: str,
        monitor: str,
        symbol: str,
        value: Optional[float],
        threshold: Optional[float],
        side: Optional[str] = None,
        extra: Optional[str] = None,
    ) -> Dict[str, Any]:
        return upsert_open(
            self.dl,
            kind=kind,
            monitor=monitor,
            symbol=symbol,
            value=value,
            threshold=threshold,
            side=side,
            extra=extra,
        )

    def resolve_open(
        self,
        *,
        kind: str,
        monitor: str,
        symbol: str,
        side: Optional[str] = None,
    ) -> int:
        return resolve_open(self.dl, kind=kind, monitor=monitor, symbol=symbol, side=side)

    def list_open(
        self,
        *,
        kind: Optional[str] = None,
        monitor: Optional[str] = None,
        symbol: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return list_open(self.dl, kind=kind, monitor=monitor, symbol=symbol)

    def get_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        return get_by_id(self.dl, alert_id)

    def touch_dispatch(self, alert_id: str) -> None:
        touch_dispatch(self.dl, alert_id)

    def record_attempt(
        self,
        *,
        alert_id: str,
        channel: str,
        provider: str,
        status: str,
        http_status: Optional[int] = None,
        error_code: Optional[str] = None,
        error_msg: Optional[str] = None,
    ) -> Dict[str, Any]:
        return record_attempt(
            self.dl,
            alert_id=alert_id,
            channel=channel,
            provider=provider,
            status=status,
            http_status=http_status,
            error_code=error_code,
            error_msg=error_msg,
        )
