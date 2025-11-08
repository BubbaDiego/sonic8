# backend/core/webterm_core/__init__.py
from .manager import ensure_running
from .autostart import autostart

__all__ = ["ensure_running", "autostart"]
