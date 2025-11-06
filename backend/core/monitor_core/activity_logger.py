# backend/core/monitor_core/activity_logger.py
# Lightweight, UI-agnostic activity logger for one monitor cycle.
# Emits start/end events so UIs (e.g., CycleActivityStream) can update live tables.

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence


@dataclass
class Activity:
    id: int
    name: str
    icon: str = "🔵"
    status: str = "pending"          # "pending" | "running" | "success" | "fail" | "warn"
    started_at: float = 0.0
    ended_at: Optional[float] = None
    duration_s: float = 0.0
    error: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "status": self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_s": self.duration_s,
            "error": self.error,
            "meta": self.meta or {},
        }


class ActivityLogger:
    """
    Single-cycle activity collector with event callbacks.

    Example:
        log = ActivityLogger()
        log.add_listener(stream.on_activity_event)
        log.begin_cycle(1)
        with log.step("Fetching positions", icon="🔵"):
            ...
        summary = log.end_cycle()
    """

    def __init__(self) -> None:
        self._acts: List[Activity] = []
        self._listeners: List[Callable[[str, Dict[str, Any]], None]] = []
        self._cycle_id: Optional[int] = None
        self._cycle_started_at: Optional[float] = None

    # ---------- public API --------------------------------------------------

    def add_listener(self, cb: Callable[[str, Dict[str, Any]], None]) -> None:
        """Register a callback(event_name, payload_dict) to mirror activity events."""
        if cb not in self._listeners:
            self._listeners.append(cb)

    def begin_cycle(self, cycle_id: int) -> None:
        self._cycle_id = cycle_id
        self._cycle_started_props_reset()

    def step(self, name: str, icon: Optional[str] = None,
             meta: Optional[Dict[str, Any]] = None) -> Step:
        """Context manager that starts + stops an activity around a code block."""
        return Step(self, name=name, icon=icon or "🔵", meta=meta or {})

    def record(self, name: str, duration_s: float, status: str = "success",
               icon: Optional[str] = None, error: Optional[str] = None,
               meta: Optional[Dict[str, Any]] = None) -> int:
        """Fire-and-forget: record an activity with a known duration."""
        idx = self._start(name=name, icon=icon or "🔵", meta=meta or {})
        self._end(idx, status=status, error=error, override_duration=duration_s)
        return idx

    def end_cycle(self) -> Dict[str, Any]:
        ts = time.time()
        self._emit("cycle_end", {"cycle_id": self._cycle_id, "ts": ts, "count": len(self._acts)})
        return {
            "id": self._safe_int(self._cycle_id),
            "started_at": self._cycle_started_at,
            "ended_at": ts,
            "activities": [a.to_dict() for a in self._acts],
        }

    def activities(self) -> Sequence[Activity]:
        return tuple(self._acts)

    # ---------- internals ---------------------------------------------------

    def _cycle_started_props_reset(self) -> None:
        self._cycle_started_at = time.time()
        self._acts.clear()
        self._emit("cycle_begin", {"cycle_id": self._cycle_id, "ts": self._cycle_started_at})

    @staticmethod
    def _safe_int(v: Any) -> Optional[int]:
        try:
            return int(v) if v is not None else None
        except Exception:
            return None

    def _emit(self, event: str, payload: Dict[str, Any]) -> None:
        for cb in list(self._listeners):
            try:
                cb(event, dict(payload))
            except Exception:
                # never let UI callbacks break logging
                pass

    def _start(self, name: str, icon: str, meta: Optional[Dict[str, Any]]) -> int:
        idx = len(self._acts)
        act = Activity(id=idx, name=name, icon=icon, status="running",
                       started_at=time.time(), meta=meta or {})
        self._acts.append(act)
        self._emit("step_start", act.to_dict())
        return idx

    def _end(self, idx: int, status: str, error: Optional[str] = None,
             override_duration: Optional[float] = None) -> None:
        act = self._acts[idx]
        act.status = status
        act.ended_at = time.time()
        act.duration = act.ended_at - act.started_at if override_duration is None else float(override_duration)
        act.duration_s = max(0.0, act.duration)
        act.error = error
        self._emit("step_end", act.to_dict())


class Step:
    """Context manager returned by ActivityLogger.step()."""

    def __init__(self, logger: ActivityLogger, name: str, icon: str, meta: Dict[str, Any]) -> None:
        self._logger = logger
        self._name = name
        self._icon = icon
        self._meta = meta
        self._idx: Optional[int] = None

    def __enter__(self) -> "Step":
        self._idx = self._logger._start(self._name, self._icon, self._meta)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self._idx is None:
            return False
        if exc_type is None:
            self._logger._end(self._idx, status="success")
            return False
        self._logger._end(self._idx, status="fail", error=str(exc))
        # propagate exception
        return False
