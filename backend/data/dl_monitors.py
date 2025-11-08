# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional
import json
from datetime import datetime, timezone

from backend.models.monitor_status import MonitorStatus


class DLMonitorsManager:
    """
    DB manager for monitor statuses (normalized table).
    - monitor_status table holds row-per-item for each cycle.
    - monitor_run (optional) can aggregate per-cycle counts (future use).
    """

    def __init__(self, db: Any):
        self.db = db
        self._ensure_schema()

    # ---------- schema ----------
    def _ensure_schema(self) -> None:
        cur = self.db.get_cursor()
        if not cur:
            return

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS monitor_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id TEXT,
                ts TEXT,
                monitor TEXT,
                label TEXT,
                state TEXT,
                value REAL,
                unit TEXT,
                thr_op TEXT,
                thr_value REAL,
                thr_unit TEXT,
                source TEXT,
                meta TEXT
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ms_cycle ON monitor_status(cycle_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ms_state ON monitor_status(state)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ms_monitor ON monitor_status(monitor)")
        self.db.commit()

        # summary table (reserved for later)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS monitor_run (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id TEXT,
                started_at TEXT,
                ended_at TEXT,
                ok_count INTEGER,
                warn_count INTEGER,
                breach_count INTEGER,
                snooze_count INTEGER,
                version TEXT,
                meta TEXT
            )
            """
        )
        self.db.commit()

    # ---------- writers ----------
    def append(self, status: MonitorStatus) -> int:
        row = status.to_row()
        cur = self.db.get_cursor()
        cur.execute(
            """
            INSERT INTO monitor_status
            (cycle_id, ts, monitor, label, state, value, unit, thr_op, thr_value, thr_unit, source, meta)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["cycle_id"],
                row["ts"],
                row["monitor"],
                row["label"],
                row["state"],
                row["value"],
                row["unit"],
                row["thr_op"],
                row["thr_value"],
                row["thr_unit"],
                row["source"],
                json.dumps(row["meta"], separators=(",", ":"), ensure_ascii=False),
            ),
        )
        self.db.commit()
        return cur.lastrowid or 0

    def append_many(self, statuses: Iterable[MonitorStatus]) -> int:
        cur = self.db.get_cursor()
        count = 0
        for s in statuses:
            r = s.to_row()
            cur.execute(
                """
                INSERT INTO monitor_status
                (cycle_id, ts, monitor, label, state, value, unit, thr_op, thr_value, thr_unit, source, meta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r["cycle_id"], r["ts"], r["monitor"], r["label"], r["state"],
                    r["value"], r["unit"], r["thr_op"], r["thr_value"], r["thr_unit"],
                    r["source"], json.dumps(r["meta"], separators=(",", ":"), ensure_ascii=False)
                ),
            )
            count += 1
        self.db.commit()
        return count

    # ---------- readers ----------
    def latest(self, cycle_id: Optional[str] = None) -> List[Dict[str, Any]]:
        cur = self.db.get_cursor()
        if not cycle_id:
            cur.execute("SELECT MAX(cycle_id) FROM monitor_status")
            row = cur.fetchone()
            cycle_id = row[0] if row and row[0] else None
            if not cycle_id:
                return []
        cur.execute(
            "SELECT cycle_id, ts, monitor, label, state, value, unit, thr_op, thr_value, thr_unit, source, meta "
            "FROM monitor_status WHERE cycle_id = ? ORDER BY id ASC",
            (cycle_id,),
        )
        cols = [c[0] for c in cur.description]
        out = []
        for r in cur.fetchall():
            d = dict(zip(cols, r))
            try:
                d["meta"] = json.loads(d["meta"] or "{}")
            except Exception:
                d["meta"] = {}
            out.append(d)
        return out

    def counts_latest(self) -> Dict[str, int]:
        cur = self.db.get_cursor()
        cur.execute("SELECT MAX(cycle_id) FROM monitor_status")
        row = cur.fetchone()
        if not row or not row[0]:
            return {"OK": 0, "WARN": 0, "BREACH": 0, "SNOOZE": 0}
        cid = row[0]
        cur.execute("SELECT state, COUNT(*) FROM monitor_status WHERE cycle_id = ? GROUP BY state", (cid,))
        counts = {"OK": 0, "WARN": 0, "BREACH": 0, "SNOOZE": 0}
        for state, c in cur.fetchall():
            s = (state or "OK").upper()
            counts[s] = int(c or 0)
        return counts
