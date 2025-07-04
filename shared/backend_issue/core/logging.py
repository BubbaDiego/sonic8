"""Project-wide console logging utilities."""

from __future__ import annotations

import logging

from backend.utils.console_logger import ConsoleLogger

# Public API ---------------------------------------------------------------
log = ConsoleLogger


def configure_console_log(debug: bool = False) -> None:
    """Configure the console logger."""
    level = "DEBUG" if debug else "INFO"
    ConsoleLogger.set_level(level)


__all__ = ["log", "configure_console_log"]
