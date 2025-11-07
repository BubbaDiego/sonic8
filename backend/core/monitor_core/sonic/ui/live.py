# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any

class SonicMonitorLive:
    """Minimal live console placeholder. Extend as you like."""
    def __init__(self, enabled: bool = False):
        self.enabled = bool(enabled)
    def write(self, msg: str) -> None:
        if self.enabled:
            print(msg)
