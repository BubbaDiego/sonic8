"""Backward-compatible wrapper for launching the Cyclone console."""

from .cyclone_console_service import run_cyclone_console


def run_console() -> None:
    """Invoke :func:`run_cyclone_console` for legacy callers."""
    run_cyclone_console()

