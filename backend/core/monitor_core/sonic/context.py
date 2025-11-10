# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.core.monitor_core.resolver.threshold_resolver import ThresholdResolver

@dataclass
class MonitorContext:
    dl: Any
    cfg: Dict[str, Any] = field(default_factory=dict)
    cfg_path_hint: Optional[str] = None
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("sonic.engine"))
    debug: bool = False
    cycle_started_at: Optional[str] = None
    cycle_id: Optional[str] = None
    resolver: Optional["ThresholdResolver"] = None
    resolve_traces: List[Dict[str, Any]] = field(default_factory=list)
    extras: Dict[str, Any] = field(default_factory=dict)

    def start_cycle(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.cycle_started_at = now
        self.cycle_id = now.replace(":", "").replace("-", "")
        self.logger.debug("Cycle start", extra={"cycle_id": self.cycle_id})
        self.resolve_traces.clear()
        self.extras.clear()

    def setdefault(self, key: str, default: Any) -> Any:
        if key == "resolve_traces":
            if not self.resolve_traces:
                self.resolve_traces = []
            return self.resolve_traces
        if key == "cfg_path_hint":
            if self.cfg_path_hint is None:
                self.cfg_path_hint = default
            return self.cfg_path_hint
        return self.extras.setdefault(key, default)

    def get(self, key: str, default: Any = None) -> Any:
        if key == "resolve_traces":
            return self.resolve_traces if self.resolve_traces else default
        if key == "cfg_path_hint":
            return self.cfg_path_hint if self.cfg_path_hint is not None else default
        return self.extras.get(key, default)

    def add_resolve_traces(self, traces: List[Dict[str, Any]]) -> None:
        for tr in traces or []:
            if tr is not None:
                self.resolve_traces.append(tr)
