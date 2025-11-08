# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional
import json
from urllib.parse import urlparse

from backend.models.xcom_message import XComMessage


# column → (type, default_sql_literal)
REQUIRED_COLUMNS = {
    "ts":                    ("TEXT",  None),
    "provider":              ("TEXT",  None),
    "direction":             ("TEXT",  None),
    "message_type":          ("TEXT",  None),
    "to_addr":               ("TEXT",  "NULL"),
    "from_addr":             ("TEXT",  "NULL"),
    "endpoint":              ("TEXT",  "NULL"),
    "status":                ("TEXT",  None),
    "error_code":            ("TEXT",  "NULL"),
    "error_msg":             ("TEXT",  "NULL"),
    "duration_ms":           ("INTEGER", "NULL"),
    "cost":                  ("REAL", "NULL"),
    "attempt":               ("INTEGER", "NULL"),
    "retries":               ("INTEGER", "NULL"),
    "internal_message_id":   ("TEXT", "NULL"),
    "external_message_id":   ("TEXT", "NULL"),
    "correlation_id":        ("TEXT", "NULL"),
    "source":                ("TEXT", "NULL"),
    "meta":                  ("TEXT", "'{}'"),
}


class DLXComManager:
    """
    DB-first XCom message store.
    - masks PII at write time
    - self-heals schema (adds columns if missing)
    - fast 'latest' queries for panel
    """

    def __init__(self, db: Any):
        self.db = db
        self._ensure_schema()

    # ---------- schema ----------
    def _ensure_schema(self) -> None:
        cur = self.db.get_cursor()
        if not cur:
            return

        # Create table if missing
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS xcom_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT,
                provider TEXT,
                direction TEXT,
                message_type TEXT,
                to_addr TEXT,
                from_addr TEXT,
                endpoint TEXT,
                status TEXT,
                error_code TEXT,
                error_msg TEXT,
                duration_ms INTEGER,
                cost REAL,
                attempt INTEGER,
                retries INTEGER,
                internal_message_id TEXT,
                external_message_id TEXT,
                correlation_id TEXT,
                source TEXT,
                meta TEXT
            )
            """
        )
        self.db.commit()

        # Add missing columns (legacy DBs)
        cur.execute("PRAGMA table_info(xcom_messages)")
        existing = {row[1] for row in cur.fetchall()}
        for name, (col_type, default_sql) in REQUIRED_COLUMNS.items():
            if name not in existing:
                if default_sql is None:
                    cur.execute(f"ALTER TABLE xcom_messages ADD COLUMN {name} {col_type}")
                else:
                    cur.execute(f"ALTER TABLE xcom_messages ADD COLUMN {name} {col_type} DEFAULT {default_sql}")
        self.db.commit()

        # Indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_xcom_ts ON xcom_messages(ts)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_xcom_provider_ts ON xcom_messages(provider, ts)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_xcom_status_ts ON xcom_messages(status, ts)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_xcom_dir_ts ON xcom_messages(direction, ts)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_xcom_corr ON xcom_messages(correlation_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_xcom_ext ON xcom_messages(external_message_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_xcom_source_ts ON xcom_messages(source, ts)")
        self.db.commit()

    # ---------- PII masking ----------
    @staticmethod
    def _mask_phone(s: Optional[str]) -> Optional[str]:
        if not s:
            return s
        t = "".join(ch for ch in str(s) if ch.isdigit() or ch == "+")
        if len(t) < 4:
            return t
        return t[:-4].replace(t[:-4], "*" * len(t[:-4])) + t[-4:]

    @staticmethod
    def _mask_email(s: Optional[str]) -> Optional[str]:
        if not s:
            return s
        txt = str(s)
        if "@" not in txt:
            return txt
        name, dom = txt.split("@", 1)
        if not name:
            return "***@" + dom
        head = name[0]
        return head + "***@" + dom

    @staticmethod
    def _short_endpoint(s: Optional[str]) -> Optional[str]:
        if not s:
            return s
        try:
            u = urlparse(str(s))
            host = u.netloc or u.path
            if len(host) > 28:
                return host[:24] + "…"
            return host
        except Exception:
            return s

    def _mask_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        # mask to_addr / from_addr (phone/email)
        def mask_any(addr: Optional[str]) -> Optional[str]:
            if not addr:
                return addr
            a = str(addr)
            return self._mask_phone(a) if any(ch.isdigit() for ch in a) else self._mask_email(a)

        row["to_addr"]   = mask_any(row.get("to_addr"))
        row["from_addr"] = mask_any(row.get("from_addr"))
        row["endpoint"]  = self._short_endpoint(row.get("endpoint"))
        return row

    # ---------- writers ----------
    def append(self, msg: XComMessage) -> int:
        row = self._mask_row(msg.to_row())
        cur = self.db.get_cursor()
        cur.execute(
            """
            INSERT INTO xcom_messages
            (ts, provider, direction, message_type, to_addr, from_addr, endpoint, status,
             error_code, error_msg, duration_ms, cost, attempt, retries,
             internal_message_id, external_message_id, correlation_id, source, meta)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["ts"], row["provider"], row["direction"], row["message_type"],
                row["to_addr"], row["from_addr"], row["endpoint"], row["status"],
                row["error_code"], row["error_msg"], row["duration_ms"], row["cost"], row["attempt"], row["retries"],
                row["internal_message_id"], row["external_message_id"], row["correlation_id"], row["source"],
                json.dumps(row["meta"], separators=(",", ":"), ensure_ascii=False),
            ),
        )
        self.db.commit()
        return cur.lastrowid or 0

    def append_many(self, messages: Iterable[XComMessage]) -> int:
        cur = self.db.get_cursor()
        n = 0
        for m in messages:
            row = self._mask_row(m.to_row())
            cur.execute(
                """
                INSERT INTO xcom_messages
                (ts, provider, direction, message_type, to_addr, from_addr, endpoint, status,
                 error_code, error_msg, duration_ms, cost, attempt, retries,
                 internal_message_id, external_message_id, correlation_id, source, meta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["ts"], row["provider"], row["direction"], row["message_type"],
                    row["to_addr"], row["from_addr"], row["endpoint"], row["status"],
                    row["error_code"], row["error_msg"], row["duration_ms"], row["cost"], row["attempt"], row["retries"],
                    row["internal_message_id"], row["external_message_id"], row["correlation_id"], row["source"],
                    json.dumps(row["meta"], separators=(",", ":"), ensure_ascii=False),
                ),
            )
            n += 1
        self.db.commit()
        return n

    # ---------- readers ----------
    def latest(self, limit: int = 30, provider: Optional[str] = None,
               direction: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        cur = self.db.get_cursor()
        q = "SELECT ts, provider, direction, message_type, to_addr, from_addr, endpoint, status, source, meta FROM xcom_messages"
        where = []
        args: List[Any] = []
        if provider:
            where.append("provider = ?")
            args.append(provider.lower())
        if direction:
            where.append("direction = ?")
            args.append(direction.upper())
        if status:
            where.append("status = ?")
            args.append(status.upper())
        if where:
            q += " WHERE " + " AND ".join(where)
        q += " ORDER BY ts DESC LIMIT ?"
        args.append(int(limit))
        cur.execute(q, tuple(args))
        cols = [c[0] for c in cur.description]
        res = [dict(zip(cols, r)) for r in cur.fetchall()]
        # ensure meta is dict
        for d in res:
            md = d.get("meta")
            if isinstance(md, str):
                try: d["meta"] = json.loads(md)
                except: d["meta"] = {}
            elif md is None:
                d["meta"] = {}
        return res

    def get_by_correlation_id(self, corr_id: str) -> List[Dict[str, Any]]:
        cur = self.db.get_cursor()
        cur.execute(
            "SELECT * FROM xcom_messages WHERE correlation_id = ? ORDER BY ts ASC",
            (corr_id,),
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def update_status_by_external_id(self, external_id: str, status: str, receipt_meta: Optional[Dict[str, Any]] = None) -> int:
        cur = self.db.get_cursor()
        meta_json = json.dumps(receipt_meta or {}, separators=(",", ":"), ensure_ascii=False)
        cur.execute(
            "UPDATE xcom_messages SET status = ?, meta = COALESCE(meta, '{}') WHERE external_message_id = ?",
            (status.upper(), external_id),
        )
        # Optionally merge meta; keeping simple: write receipt_meta if provided
        if receipt_meta:
            cur.execute(
                "UPDATE xcom_messages SET meta = ? WHERE external_message_id = ?",
                (meta_json, external_id),
            )
        self.db.commit()
        return cur.rowcount or 0
