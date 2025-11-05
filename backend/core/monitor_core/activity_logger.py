from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class Activity:
    name: str
    icon: str = "🔵"
    status: str = "success"
    started_at: float = 0.0
    ended_at: float = 0.0
    duration_s: float = 0.0
    error: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Step:
    """Context manager for timing and status capture."""

    def __init__(self, logger: "ActivityLogger", name: str, icon: Optional[str] = None, meta: Optional[Dict[str, Any]] = None):
        self.logger = logger
        self.name = name
        self.icon = icon or "🔵"
        self.meta = meta or {}
        self._idx: Optional[int] = None

    def __enter__(self) -> "Step":
        self._idx = self.logger._start(self.name, self.icon, self.meta)
        return self

    def success(self) -> None:
        if self._idx is not None:
            self.logger._end(self._idx, status="success")
            self._idx = None

    def warn(self, msg: Optional[str] = None) -> None:
        if self._idx is not None:
            self.logger._end(self._idx, status="warn", error=msg)
            self._idx = None

    def fail(self, err: Optional[str] = None) -> None:
        if self._idx is not None:
            self.logger._end(self._idx, status="fail", error=err)
            self._idx = None

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self._idx is None:
            return False
        if exc_type is None:
            self.logger._end(self._idx, status="success")
            return False
        self.logger._end(self._idx, status="fail", error=str(exc))
        return False


class ActivityLogger:
    """Collects step activities for a single monitor cycle."""

    def __init__(self) -> None:
        self._acts: List[Activity] = []
        self._cycle_id: Optional[int] = None
        self._cycle_started_at: Optional[float] = None

    def begin_cycle(self, cycle_id: int) -> None:
        self._cycle_id = cycle_id
        self._cycle_started_at = time.time()
        self._acts.clear()

    def step(self, name: str, icon: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> Step:
        return Step(self, name=name, icon=icon, meta=meta)

    def record(self, name: str, duration_s: float, status: str = "success", icon: Optional[str] = None,
               error: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> None:
        idx = self._start(name, icon or "🔵", meta or {})
        self._end(idx, status=status, error=error, override_duration=duration_s)

    def end_cycle(self) -> Dict[str, Any]:
        return {
            "id": self._cycle_id,
            "started_at": self._cycle_started_at,
            "activities": [a.to_dict() for a in self._acts],
        }

    def activities(self) -> Sequence[Activity]:
        return tuple(self._acts)

    def _start(self, name: str, icon: str, meta: Optional[Dict[str, Any]]) -> int:
        act = Activity(name=name, icon=icon, meta=meta or {}, started_at=time.time())
        self._acts.append(act)
        return len(self._acts) - 1

    def _end(self, idx: int, status: str, error: Optional[str] = None, override_duration: Optional[float] = None) -> None:
        act = self._acts[idx]
        act.status = status
        act.ended_at = time.time()
        act.duration_s = override_duration if override_duration is not None else max(0.0, act.ended_at - act.started_at)
        act.error = error
