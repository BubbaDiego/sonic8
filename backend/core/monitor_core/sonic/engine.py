# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Callable, Tuple
from datetime import datetime, timezone

from .context import MonitorContext
from .registry import get_enabled_monitors, get_enabled_services
from .storage.heartbeat_store import HeartbeatStore
from .storage.ledger_store import LedgerStore
from .storage.activity_store import ActivityStore  # keeps Cycle Activity panel fed
from .reporting.console.runner import run_console_reporters
from backend.models.monitor_status import MonitorStatus
from backend.core.monitor_core.resolver import ThresholdResolver
from backend.core.monitor_core.xcom_bridge import dispatch_breaches_from_dl
from backend.core.core_constants import SONIC_MONITOR_CONFIG_PATH


def _load_monitor_cfg() -> Tuple[Dict[str, Any], str]:
    try:
        with SONIC_MONITOR_CONFIG_PATH.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
        logging.getLogger("sonic.engine").info(
            "[resolve] cfg path: %s", SONIC_MONITOR_CONFIG_PATH
        )
        return cfg, str(SONIC_MONITOR_CONFIG_PATH)
    except Exception as e:
        logging.getLogger("sonic.engine").info("[resolve] cfg load failed: %s", e)
        return {}, "<unknown>"


class MonitorEngine:
    """
    Sonic monitor engine (DB-first).

      • runs Cyclone.run_cycle() (prices/positions/hedges/etc)
      • runs services (raydium/hedges/…)
      • runs monitors (profit/liquid/market/…)
      • records activity rows for the Cycle Activity panel
      • persists monitor statuses to DB (via dl.monitors)
      • renders console reporters (DB reads)

    Spinners/debug are OFF by default to keep the console clean.
    Toggle with SONIC_LIVE=1 if you want them back.
    """

    DEBUG: bool = os.getenv("SONIC_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}

    def __init__(self, dl: Any, cfg: Optional[Dict[str, Any]] = None, debug: Optional[bool] = None) -> None:
        self.dl = dl
        self.cfg = cfg or {}
        self.debug = self.DEBUG if debug is None else bool(debug)

        self.logger = logging.getLogger("sonic.engine")
        self.logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        if not self.logger.handlers:
            h = logging.StreamHandler()
            h.setFormatter(
                logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
            )
            self.logger.addHandler(h)

        self.ctx = MonitorContext(dl=self.dl, cfg=self.cfg, logger=self.logger, debug=self.debug)
        self.heartbeat = HeartbeatStore(self.dl, self.logger)
        self.ledger = LedgerStore(self.dl, self.logger)
        self.activities = ActivityStore(self.dl, self.logger)

        # Keep console clean by default (no spinners)
        self.live_enabled = os.getenv("SONIC_LIVE", "0").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        # Lazily created Cyclone engine (shared across cycles)
        self._cyclone: Optional[Any] = None

    # ───────────────────────── helpers ─────────────────────────

    def _ensure_cyclone(self) -> Any:
        """
        Lazily create a Cyclone engine wired to the same DataLocker as Sonic Monitor.
        """
        if self._cyclone is not None:
            return self._cyclone

        try:
            from backend.core.cyclone_core import cyclone_engine as _ce  # type: ignore

            dl_obj = self.dl
            try:
                # Force Cyclone to share the same DataLocker instance
                if hasattr(_ce, "global_data_locker") and dl_obj is not None:
                    _ce.global_data_locker = dl_obj  # type: ignore[assignment]
            except Exception:
                self.logger.debug(
                    "[cyclone] failed to patch global_data_locker", exc_info=True
                )

            self._cyclone = _ce.Cyclone(debug=self.debug)
            return self._cyclone
        except Exception as exc:
            self.logger.exception("[cyclone] failed to initialize Cyclone engine: %s", exc)
            raise

    # ───────────────────────── cycle ─────────────────────────

    def run_once(self) -> None:
        self.ctx.start_cycle()
        cycle_id = self.ctx.cycle_id or "unknown"
        cycle_t0 = time.monotonic()
        cfg, cfg_path_hint = _load_monitor_cfg()
        self.cfg = cfg
        self.ctx.cfg = cfg
        self.ctx.cfg_path_hint = cfg_path_hint
        self.ctx.resolver = ThresholdResolver(self.cfg, self.dl, cfg_path_hint=cfg_path_hint)
        self.logger.info(
            "[resolve] cfg path: %s",
            self.ctx.resolver.cfg_path_hint or "<unknown>",
        )

        bus_rows: List[Dict[str, Any]] = []

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
                self.activities.end(
                    tok,
                    outcome=outcome,
                    notes=notes,
                    duration_ms=dt_ms,
                    details=details,
                )

        # 0) Cyclone engine (authoritative prices/positions/hedges pipeline)
        def _run_cyclone() -> Dict[str, Any]:
            start = time.monotonic()
            try:
                cyclone = self._ensure_cyclone()
                asyncio.run(cyclone.run_cycle())
                duration = time.monotonic() - start
                self.logger.info(
                    "🌀 Cyclone.run_cycle completed in %.2fs (cycle=%s)",
                    duration,
                    cycle_id,
                )
                return {
                    "ok": True,
                    "source": "Cyclone.run_cycle",
                    "duration": duration,
                }
            except Exception as exc:
                duration = time.monotonic() - start
                self.logger.exception("[cyclone] run_cycle failed: %s", exc)
                return {
                    "ok": False,
                    "source": "Cyclone.run_cycle",
                    "duration": duration,
                    "error": str(exc),
                }

        _run_phase("cyclone", "Cyclone run_cycle", _run_cyclone)

        # 1) services (raydium/hedges – prices & positions handled by Cyclone now)
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
                    ms_rows: List[MonitorStatus] = []
                    bus_payload: List[Dict[str, Any]] = []
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
                        bus_payload.append(ms.to_row())
                    if ms_rows and mm is not None:
                        mm.append_many(ms_rows)
                    if bus_payload:
                        bus_rows.extend(bus_payload)
                return out

            _run_phase(name, f"{name.capitalize()} monitor", _run_mon)

        mgr = getattr(self.dl, "dl_monitors", None) or getattr(self.dl, "monitors", None)
        payload = list(bus_rows)
        if mgr is not None:
            for meth in ("replace", "set_rows", "reset", "update_rows"):
                fn = getattr(mgr, meth, None)
                if callable(fn):
                    fn(payload)
                    break
            else:
                try:
                    setattr(mgr, "rows", payload)
                except Exception:
                    pass
        else:
            self.logger.info("[mon] no dl_monitors manager on DataLocker; cannot publish")

        self.logger.info("[mon] dl_monitors updated")
        self.logger.info("[mon] dl_monitors rows after evaluate = %d", len(payload))

        sent = dispatch_breaches_from_dl(self.dl, self.cfg)
        self.logger.info("[xcom] sent %d notifications", len(sent))

        sysmgr = getattr(self.dl, "system", None)
        if sysmgr and hasattr(sysmgr, "set_var"):
            try:
                sysmgr.set_var("xcom_last_sent", sent)
            except Exception as exc:
                self.logger.info("[xcom] failed to record last sent: %s", exc)

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
        run_console_reporters(self.dl, self.debug, footer_ctx=footer_ctx, cfg=self.cfg)

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

        cfg_obj, cfg_path_hint = _load_monitor_cfg()
        ctx = {
            "dl": self.dl,
            "cfg": cfg_obj,
            "cfg_path_hint": cfg_path_hint,
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
        self.logger.info(
            "Sonic Monitor engine starting (interval=%ss, debug=%s)",
            interval_sec,
            self.debug,
        )
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
                from backend.core.reporting_core.sonic_reporting.console_panels import (
                    transition_panel as _trans,
                )

                _trans.run(
                    {
                        "poll_interval_s": interval_sec,
                    }
                )
            except Exception:
                time.sleep(interval_sec)
