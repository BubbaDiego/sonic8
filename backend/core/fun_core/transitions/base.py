# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional
import os

@dataclass
class TransitionContext:
    duration_s: int = int(os.getenv("FUN_TRANSITIONS_DURATION_S", "60"))
    fps: int = int(os.getenv("FUN_TRANSITIONS_FPS", "12"))
    width: int = 0   # 0 => auto
    height: int = 0  # 0 => auto
    color: bool = os.getenv("FUN_TRANSITIONS_COLOR", "1") not in {"0","false","False","no","NO"}
    emoji: bool = os.getenv("FUN_TRANSITIONS_EMOJI", "1") not in {"0","false","False","no","NO"}
    title: Optional[str] = None
    # Supplier for a fun one-liner
    get_fun_line: Optional[Callable[[], str]] = None
    # Testability hooks
    now: Optional[Callable[[], float]] = None
    # Optional theme override (see themes.py)
    theme: Optional[object] = None
