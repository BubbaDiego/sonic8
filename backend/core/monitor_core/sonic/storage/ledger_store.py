# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from typing import Any, Dict
import logging

class LedgerStore:
    def __init__(self, dl: Any, logger: logging.Logger) -> None:
        self.dl = dl
        self.logger = logger
        self._ensure_table()

    def _ensure_table(self) -> None:
        try:
            cur = self.dl.db.get_cursor()
            cur.execute("""
              CREATE TABLE IF NOT EXISTS sonic_monitor_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_id TEXT,
                name TEXT,
                payload TEXT
              )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sml_cycle ON sonic_monitor_ledger(cycle_id)")
            self.dl.db.commit()
        except Exception as e:
            self.logger.debug(f"ledger table ensure skipped: {e}")

    def append_monitor_result(self, cycle_id: str, name: str, result: Dict[str, Any]) -> None:
        try:
            payload = json.dumps(result, separators=(",", ":"), ensure_ascii=False)
            cur = self.dl.db.get_cursor()
            cur.execute("INSERT INTO sonic_monitor_ledger (cycle_id, name, payload) VALUES (?, ?, ?)",
                        (cycle_id, name, payload))
            self.dl.db.commit()
        except Exception as e:
            self.logger.debug(f"ledger append failed: {e}")
