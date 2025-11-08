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
from .storage.activity_store import ActivityStore
from .reporting.console.runner import run_console_reporters
from .ui.live import SonicMonitorLive

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
        self.activities = ActivityStore(self.dl, self.logger)
        self.live = SonicMonitorLive(enabled=not bool(os.getenv("SONIC_NO_LIVE")))

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

        # helper to run a phase with spinner + activity rows
        def _run_phase(phase_key: str, label: str, fn):
            tok = self.activities.begin(cycle_id, phase_key, label)
            sp = self.live.start_spinner(phase_key, label)
            t0 = time.time()
            outcome = "ok"
            notes = ""
            details: Dict[str, Any] = {}
            try:
                res = fn()
                details = res if isinstance(res, dict) else {"result": str(res)}
                # build a short note when possible
                if "count" in details:
                    notes = f"count {details['count']}"
                elif "result" in details and isinstance(details["result"], dict) and "count" in details["result"]:
                    notes = f"count {details['result']['count']}"
                elif "result" in details and isinstance(details["result"], dict) and "note" in details["result"]:
                    notes = details["result"]["note"] or ""
            except Exception as e:
                outcome = "error"
                notes = f"{type(e).__name__}: {e}"
                self.logger.exception(f"[phase] {phase_key} failed: {e}")
            finally:
                dt = time.time() - t0
                self.activities.end(
                    tok,
                    outcome=outcome,
                    notes=notes,
                    duration_ms=int(dt * 1000),
                    details=details,
                )
                # stop spinner silently; Cycle Activity table will show outcome/time
                self.live.stop_spinner(sp)

        # 1) services (populate DB)
        services = get_enabled_services(self.cfg)
        for name, svc in services:
            _run_phase(name, f"{name.capitalize()} service", lambda svc=svc: svc(self.ctx))

        # 2) monitors (compute + persist status)
        monitors = get_enabled_monitors(self.cfg)
        for name, runner in monitors:
            def _run_mon(runner=runner, name=name):
                r = runner(self.ctx)  # expected contract: dict with optional 'statuses': List[dict]
                self.ledger.append_monitor_result(cycle_id, name, r)
                # optional: persist normalized statuses if provided
                try:
                    statuses = r.get("statuses") if isinstance(r, dict) else None
                    if isinstance(statuses, list) and statuses:
                        try:
                            from .storage.monitor_status_store import MonitorStatusStore

                            MonitorStatusStore(self.dl, self.logger).append_many(cycle_id, name, statuses)
                        except Exception:
                            pass
                except Exception as e:
                    self.logger.debug(f"status persist failed for {name}: {e}")
                # construct lightweight notes
                note = ""
                if isinstance(r, dict) and isinstance(r.get("statuses"), list):
                    note = f"{len(r['statuses'])} status"
                return {"result": {"note": note}}

            _run_phase(name, f"{name.capitalize()} monitor", _run_mon)

        # 3) heartbeat
        _run_phase("heartbeat", "Heartbeat", lambda: (self.heartbeat.touch() or {"ok": True}))

        # 4) reporters (console panels) — DB-first, no csum
        _run_phase("reporters", "Reporters", lambda: (run_console_reporters(self.dl, self.debug) or {"ok": True}))

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
