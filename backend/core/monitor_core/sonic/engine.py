# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

from .context import MonitorContext
from .registry import get_enabled_monitors, get_enabled_services
from .storage.heartbeat_store import HeartbeatStore
from .storage.ledger_store import LedgerStore
from .storage.monitor_status_store import MonitorStatusStore
from .reporting.console.runner import run_console_reporters

class MonitorEngine:
    """
    Modular Sonic monitor engine.
    - Runs services (prices/positions/raydium) to populate DB
    - Runs monitor runners (liquid/profit/market) and persists results
    - Calls console reporters at the end of each cycle

    DEBUG SWITCH (edit here or set env SONIC_DEBUG=1):
        MonitorEngine.DEBUG = False
    """
    DEBUG: bool = (os.getenv("SONIC_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"})

    def __init__(self, dl: Any, cfg: Optional[Dict[str, Any]] = None, debug: Optional[bool] = None) -> None:
        self.dl = dl
        self.cfg = cfg or {}
        self.debug = self.DEBUG if debug is None else bool(debug)
        self.logger = logging.getLogger("sonic.engine")
        self.logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        if not self.logger.handlers:
            h = logging.StreamHandler()
            fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
            h.setFormatter(fmt)
            self.logger.addHandler(h)

        self.ctx = MonitorContext(dl=self.dl, cfg=self.cfg, logger=self.logger, debug=self.debug)
        self.heartbeat = HeartbeatStore(self.dl, self.logger)
        self.ledger = LedgerStore(self.dl, self.logger)
        self.status = MonitorStatusStore(self.dl, self.logger)

    # ───────────────────────── helpers ─────────────────────────

    def dlog(self, msg: str, **kw) -> None:
        if self.debug:
            try:
                self.logger.debug(msg + (" :: " + str(kw) if kw else ""))
            except Exception:
                self.logger.debug(msg)

    # ───────────────────────── cycle ─────────────────────────

    def run_once(self) -> None:
        self.ctx.start_cycle()
        cycle_id = self.ctx.cycle_id or "unknown"

        # 1) services (populate DB)
        services = get_enabled_services(self.cfg)
        svc_results = {}
        for name, svc in services:
            try:
                self.dlog(f"[svc] start {name}")
                res = svc(self.ctx)
                svc_results[name] = res
                self.dlog(f"[svc] done {name}", result=res)
            except Exception as e:
                self.logger.exception(f"[svc] {name} failed: {e}")

        # 2) monitors (compute + persist status)
        monitors = get_enabled_monitors(self.cfg)
        mon_results = []
        for name, runner in monitors:
            try:
                self.dlog(f"[mon] start {name}")
                r = runner(self.ctx)  # expected contract: dict with optional 'statuses': List[dict]
                mon_results.append((name, r))
                self.ledger.append_monitor_result(cycle_id, name, r)
                # persist normalized statuses if provided
                try:
                    statuses = r.get("statuses") if isinstance(r, dict) else None
                    if isinstance(statuses, list) and statuses:
                        saved = self.status.append_many(cycle_id, name, statuses)
                        self.dlog(f"[mon] persisted {saved} statuses", monitor=name)
                except Exception as e:
                    self.logger.debug(f"status persist failed for {name}: {e}")
                self.dlog(f"[mon] done {name}", result=r)
            except Exception as e:
                self.logger.exception(f"[mon] {name} failed: {e}")

        # 3) heartbeat
        try:
            self.heartbeat.touch()
        except Exception as e:
            self.logger.warning(f"heartbeat failed: {e}")

        # 4) reporters (console panels) — DB-first, no csum
        try:
            run_console_reporters(self.dl, self.debug)
        except Exception as e:
            self.logger.exception(f"console reporters failed: {e}")

    def run_forever(self, interval_sec: int = 30) -> None:
        self.logger.info("Sonic Monitor engine starting (interval=%ss, debug=%s)", interval_sec, self.debug)
        while True:
            try:
                self.run_once()
            except KeyboardInterrupt:
                self.logger.info("Sonic Monitor interrupted — exiting.")
                break
            except Exception as e:
                self.logger.exception("Uncaught during run_once: %s", e)
            time.sleep(interval_sec)
