# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any
import logging

class HeartbeatStore:
    def __init__(self, dl: Any, logger: logging.Logger) -> None:
        self.dl = dl
        self.logger = logger
        self._ensure_table()

    def _ensure_table(self) -> None:
        try:
            cur = self.dl.db.get_cursor()
            cur.execute("""
              CREATE TABLE IF NOT EXISTS sonic_heartbeats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL
              )
            """)
            self.dl.db.commit()
        except Exception as e:
            self.logger.debug(f"heartbeat table ensure skipped: {e}")

    def touch(self) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        try:
            cur = self.dl.db.get_cursor()
            cur.execute("INSERT INTO sonic_heartbeats (ts) VALUES (?)", (ts,))
            self.dl.db.commit()
        except Exception as e:
            # fall back to system var if DB unavailable
            try:
                if getattr(self.dl, "system", None):
                    self.dl.system.set_var("sonic.last_heartbeat", ts)
            except Exception:
                pass
            self.logger.debug(f"heartbeat touch fallback: {e}")
