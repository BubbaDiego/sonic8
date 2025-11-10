# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timezone

from .context import MonitorContext
from .registry import get_enabled_monitors, get_enabled_services
from .storage.heartbeat_store import HeartbeatStore
from .storage.ledger_store import LedgerStore
from .storage.activity_store import ActivityStore  # keeps Cycle Activity panel fed
from .reporting.console.runner import run_console_reporters
from backend.models.monitor_status import MonitorStatus
from backend.core.monitor_core.resolver import ThresholdResolver


class MonitorEngine:
    """
    Sonic monitor engine (DB-first).
      • runs services (prices/positions/raydium/hedges/…)
      • runs monitors (profit/liquid/market/…)
      • records activity rows for the Cycle Activity panel
      • persists monitor statuses to DB (via dl.monitors)
      • renders console reporters (DB reads)

    Spinners/debug are OFF by default to keep the console clean.
    Toggle with SONIC_LIVE=1 if you want them back.
    """
    DEBUG: bool = os.getenv("SONIC_DEBUG", "0").strip().lower() in {"1","true","yes","on"}

    def __init__(self, dl: Any, cfg: Optional[Dict[str, Any]] = None, debug: Optional[bool] = None) -> None:
        self.dl = dl
        self.cfg = cfg or {}
        self.debug = self.DEBUG if debug is None else bool(debug)

        self.logger = logging.getLogger("sonic.engine")
        self.logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        if not self.logger.handlers:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))
            self.logger.addHandler(h)

        self.ctx = MonitorContext(dl=self.dl, cfg=self.cfg, logger=self.logger, debug=self.debug)
        self.heartbeat = HeartbeatStore(self.dl, self.logger)
        self.ledger = LedgerStore(self.dl, self.logger)
        self.activities = ActivityStore(self.dl, self.logger)

        # Keep console clean by default (no spinners)
        self.live_enabled = os.getenv("SONIC_LIVE", "0").strip().lower() in {"1","true","yes","on"}

    # ───────────────────────── cycle ─────────────────────────

    def run_once(self) -> None:
        self.ctx.start_cycle()
        cycle_id = self.ctx.cycle_id or "unknown"
        cycle_t0 = time.monotonic()
        self.ctx.resolver = ThresholdResolver(self.cfg, self.dl)
        self.logger.info("[resolve] cfg path: %s", self.ctx.resolver.cfg_path_hint or "<unknown>")

        def _run_phase(phase_key: str, label: str, fn: Callable[[], Dict[str, Any]]):
            tok = self.activities.begin(cycle_id, phase_key, label)
            t0 = time.monotonic()
            outcome = "ok"
            notes = ""
            details: Dict[str, Any] = {}
            try:
                res = fn() or {}
                details = res if isinstance(res, dict) else {"result": str(res)}
                # build short note
                if "count" in details and details["count"] is not None:
                    notes = f"count {details['count']}"
                elif isinstance(details.get("result"), dict) and "count" in details["result"]:
                    notes = f"count {details['result']['count']}"
                elif "statuses" in details and isinstance(details["statuses"], list):
                    notes = f"{len(details['statuses'])} status"
            except Exception as e:
                outcome = "error"
                notes = f"{type(e).__name__}: {e}"
                self.logger.exception(f"[phase] {phase_key} failed: {e}")
            finally:
                dt_ms = int((time.monotonic() - t0) * 1000)
                self.activities.end(tok, outcome=outcome, notes=notes, duration_ms=dt_ms, details=details)

        # 1) services
        for name, svc in get_enabled_services(self.cfg):
            _run_phase(name, f"{name.capitalize()} service", lambda s=svc: s(self.ctx))

        # 2) monitors (persist normalized statuses)
        for name, runner in get_enabled_monitors(self.cfg):
            def _run_mon(n=name, r=runner):
                pre_trace_len = len(getattr(self.ctx, "resolve_traces", []) or [])
                out = r(self.ctx) or {}
                if not isinstance(out, dict):
                    out = {"result": out}
                post_traces = getattr(self.ctx, "resolve_traces", []) or []
                new_traces = post_traces[pre_trace_len:]
                if new_traces:
                    trace_dicts = []
                    for t in new_traces:
                        if isinstance(t, dict):
                            trace_dicts.append(dict(t))
                        else:
                            trace_dicts.append(dict(getattr(t, "__dict__", {}) or {}))
                    existing = out.get("resolve_traces")
                    if isinstance(existing, list):
                        existing.extend(trace_dicts)
                    else:
                        out["resolve_traces"] = trace_dicts
                self.ledger.append_monitor_result(cycle_id, n, out)

                statuses = out.get("statuses") if isinstance(out, dict) else None
                if isinstance(statuses, list) and statuses:
                    now_iso = datetime.now(timezone.utc).isoformat()
                    mm = getattr(self.dl, "monitors", None)
                    if mm is not None:
                        ms_rows = []
                        for it in statuses:
                            if not isinstance(it, dict):
                                continue
                            ms = MonitorStatus.from_status_dict(
                                cycle_id=cycle_id,
                                monitor=n,
                                item=it,
                                default_label=n,
                                now_iso=now_iso,
                                default_source=n,
                            )
                            ms_rows.append(ms)
                        if ms_rows:
                            mm.append_many(ms_rows)
                return out

            _run_phase(name, f"{name.capitalize()} monitor", _run_mon)

        # 3) heartbeat
        _run_phase("heartbeat", "Heartbeat", lambda: (self.heartbeat.touch() or {"ok": True}))

        # 4) reporters (DB-first, no csum)
        elapsed = time.monotonic() - cycle_t0
        footer_ctx = {
            "loop_counter": getattr(self, "_loop_n", 0),
            "poll_interval_s": getattr(self, "_poll_interval_sec", 0),
            "total_elapsed_s": round(float(elapsed), 3),
            "ts": datetime.now().isoformat(timespec="seconds"),
        }
        run_console_reporters(self.dl, self.debug, footer_ctx=footer_ctx)

    def _run_panel_stack(self, loop_counter: int, interval: int, start_wall: float) -> None:
        """Render the reporter panel stack with explicit debug traces."""
        try:
            from backend.core.reporting_core import console_reporter as _cr
        except Exception as import_exc:
            print(f"[REPORT] panel runner failed: {import_exc!r}", flush=True)
            return

        try:
            width = int(os.environ.get("SONIC_CONSOLE_WIDTH", "92"))
        except Exception:
            width = 92

        cfg_obj = getattr(self.dl, "global_config", None)
        ctx = {
            "dl": self.dl,
            "cfg": cfg_obj,
            "loop_counter": int(loop_counter),
            "poll_interval_s": int(interval),
            "total_elapsed_s": float(max(0.0, time.time() - start_wall)),
            "ts": time.time(),
        }

        try:
            _cr.render_panel_stack(ctx=ctx, dl=self.dl, cfg=cfg_obj, width=width, writer=print)
        except Exception as exc:
            print(f"[REPORT] panel runner failed: {exc!r}", flush=True)

    def run_forever(self, interval_sec: int = 30) -> None:
        self.logger.info("Sonic Monitor engine starting (interval=%ss, debug=%s)", interval_sec, self.debug)
        self._loop_n = getattr(self, "_loop_n", 0)
        self._poll_interval_sec = interval_sec
        while True:
            try:
                self._loop_n += 1
                self.run_once()
            except KeyboardInterrupt:
                self.logger.info("Sonic Monitor interrupted — exiting.")
                break
            except Exception as e:
                self.logger.exception("Uncaught during run_once: %s", e)

            try:
                from backend.core.reporting_core.sonic_reporting.console_panels import transition_panel as _trans

                _trans.run({
                    "poll_interval_s": interval_sec,
                })
            except Exception:
                time.sleep(interval_sec)
