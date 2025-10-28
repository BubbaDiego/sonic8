from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional


class DLJupiterLogManager:
    """Minimal audit table manager for Jupiter transactions."""

    def __init__(self, locker: Any = None, db_path: Optional[Path] = None) -> None:
        self._locker = locker
        self._db_path = db_path

    # -- connection helpers -------------------------------------------------
    def _get_conn(self) -> sqlite3.Connection:
        # If locker exposes a connection, prefer it.
        # Common patterns: locker.db or locker.conn
        if self._locker is not None:
            conn = getattr(self._locker, "db", None) or getattr(self._locker, "conn", None)
            if conn is not None:
                return conn
        assert self._db_path is not None, "db_path is required when locker is None"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    # -- schema -------------------------------------------------------------
    def ensure_schema(self) -> None:
        conn = self._get_conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jupiter_txlog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT DEFAULT (datetime('now')),
                kind TEXT,
                status TEXT,
                signature TEXT,
                request_json TEXT,
                response_json TEXT,
                notes TEXT
            );
            """
        )
        conn.commit()

    # -- writes -------------------------------------------------------------
    def insert(
        self,
        *,
        kind: str,
        status: str,
        request_json: Optional[str] = None,
        response_json: Optional[str] = None,
        signature: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO jupiter_txlog (kind, status, signature, request_json, response_json, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (kind, status, signature, request_json, response_json, notes),
        )
        conn.commit()
        return int(cur.lastrowid)

    # -- reads --------------------------------------------------------------
    def tail(self, *, limit: int = 20) -> list[tuple]:
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, ts, kind, status, IFNULL(signature, ''),
                   substr(IFNULL(request_json, ''), 1, 80),
                   substr(IFNULL(response_json, ''), 1, 80)
            FROM jupiter_txlog
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return list(cur.fetchall())
