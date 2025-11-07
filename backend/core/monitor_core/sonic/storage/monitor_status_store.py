# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional
import json
import logging

class MonitorStatusStore:
    """
    Persists normalized monitor statuses per cycle.

    Schema:
      monitor_status (
        id         INTEGER PK,
        cycle_id   TEXT,
        monitor    TEXT,          -- 'liquid' | 'profit' | 'market' | ...
        label      TEXT,          -- human label (e.g., 'BTC Liquid', 'Portfolio Profit')
        state      TEXT,          -- 'OK' | 'WARN' | 'BREACH' | 'OFF' ...
        value      REAL,          -- numeric primary measure (e.g., profit %, distance-to-liq)
        unit       TEXT,          -- '%', 'USD', 'bps', etc.
        meta       TEXT           -- JSON: extra fields (asset, threshold, source)
      )

    We keep it simple and append each cycle. Reporters show the most recent cycle.
    """

    def __init__(self, dl: Any, logger: Optional[logging.Logger] = None) -> None:
        self.dl = dl
        self.logger = logger
        self._ensure_table()

    def _ensure_table(self) -> None:
        try:
            cur = self.dl.db.get_cursor()
            cur.execute("""
              CREATE TABLE IF NOT EXISTS monitor_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id TEXT,
                monitor  TEXT,
                label    TEXT,
                state    TEXT,
                value    REAL,
                unit     TEXT,
                meta     TEXT
              )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ms_cycle ON monitor_status(cycle_id)")
            self.dl.db.commit()
        except Exception as e:
            if self.logger:
                self.logger.debug(f"monitor_status ensure-table skipped: {e}")

    def append_many(self, cycle_id: str, monitor: str, rows: List[Dict[str, Any]]) -> int:
        if not rows:
            return 0
        cur = self.dl.db.get_cursor()
        count = 0
        for r in rows:
            try:
                label = str(r.get("label") or r.get("name") or "")
                state = str(r.get("state") or r.get("status") or "OK")
                unit  = str(r.get("unit")  or r.get("units")  or "")
                value = r.get("value")
                meta  = json.dumps(r, separators=(",", ":"), ensure_ascii=False)
                cur.execute(
                    "INSERT INTO monitor_status (cycle_id, monitor, label, state, value, unit, meta) VALUES (?,?,?,?,?,?,?)",
                    (cycle_id, monitor, label, state, value, unit, meta),
                )
                count += 1
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"monitor_status append failed: {e}")
        self.dl.db.commit()
        return count

    def latest_for_cycle(self, cycle_id: str) -> List[Dict[str, Any]]:
        cur = self.dl.db.get_cursor()
        cur.execute("SELECT monitor, label, state, value, unit, meta FROM monitor_status WHERE cycle_id = ?", (cycle_id,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def latest(self, limit_cycles: int = 1) -> List[Dict[str, Any]]:
        """
        If you don’t pass a specific cycle_id, show the most-recent appended rows.
        """
        cur = self.dl.db.get_cursor()
        # naive "most recent cycle" heuristic: use max(id) window
        cur.execute("SELECT MAX(cycle_id) FROM monitor_status")
        row = cur.fetchone()
        if not row or not row[0]:
            return []
        return self.latest_for_cycle(row[0])
