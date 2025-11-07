# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import json
import logging

@dataclass
class ActivityToken:
    cycle_id: str
    phase: str
    label: str
    ts_start: str

class ActivityStore:
    """
    Persists per-phase cycle activities with duration and outcome.

    Table: cycle_activities
      id           INTEGER PK
      cycle_id     TEXT
      phase        TEXT      -- machine key: prices|positions|raydium|hedges|profit|liquid|market|reporters|heartbeat|...
      label        TEXT      -- human label shown in UI
      outcome      TEXT      -- 'ok'|'warn'|'error'|'skip'
      notes        TEXT      -- short notes, compact, human-readable
      duration_ms  INTEGER
      ts_start     TEXT
      ts_end       TEXT
      details      TEXT      -- JSON (raw payload for deep debug)
    """

    def __init__(self, dl: Any, logger: Optional[logging.Logger] = None) -> None:
        self.dl = dl
        self.logger = logger
        self._ensure_table()

    def _ensure_table(self) -> None:
        try:
            cur = self.dl.db.get_cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cycle_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_id TEXT,
                    phase TEXT,
                    label TEXT,
                    outcome TEXT,
                    notes TEXT,
                    duration_ms INTEGER,
                    ts_start TEXT,
                    ts_end TEXT,
                    details TEXT
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ca_cycle ON cycle_activities(cycle_id)")
            self.dl.db.commit()
        except Exception as e:
            if self.logger:
                self.logger.debug(f"cycle_activities ensure-table skipped: {e}")

    def begin(self, cycle_id: str, phase: str, label: str) -> ActivityToken:
        return ActivityToken(
            cycle_id=cycle_id,
            phase=phase,
            label=label,
            ts_start=datetime.now(timezone.utc).isoformat(),
        )

    def end(self, token: ActivityToken, outcome: str = "ok",
            notes: str = "", duration_ms: Optional[int] = None,
            details: Optional[Dict[str, Any]] = None) -> None:
        ts_end = datetime.now(timezone.utc).isoformat()
        dur = duration_ms
        if dur is None:
            # compute from timestamps
            try:
                t0 = datetime.fromisoformat(token.ts_start.replace("Z", "+00:00"))
                t1 = datetime.fromisoformat(ts_end.replace("Z", "+00:00"))
                dur = int((t1 - t0).total_seconds() * 1000)
            except Exception:
                dur = None
        try:
            cur = self.dl.db.get_cursor()
            cur.execute(
                "INSERT INTO cycle_activities (cycle_id, phase, label, outcome, notes, duration_ms, ts_start, ts_end, details) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    token.cycle_id,
                    token.phase,
                    token.label,
                    outcome,
                    notes or "",
                    dur,
                    token.ts_start,
                    ts_end,
                    json.dumps(details or {}, separators=(",", ":"), ensure_ascii=False),
                ),
            )
            self.dl.db.commit()
        except Exception as e:
            if self.logger:
                self.logger.debug(f"cycle_activities insert failed: {e}")
