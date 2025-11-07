# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

@dataclass
class MonitorContext:
    dl: Any
    cfg: Dict[str, Any] = field(default_factory=dict)
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("sonic.engine"))
    debug: bool = False
    cycle_started_at: Optional[str] = None
    cycle_id: Optional[str] = None

    def start_cycle(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.cycle_started_at = now
        self.cycle_id = now.replace(":", "").replace("-", "")
        self.logger.debug("Cycle start", extra={"cycle_id": self.cycle_id})
