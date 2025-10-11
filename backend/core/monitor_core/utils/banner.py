from __future__ import annotations

from typing import Any


def _safe_db_path(dl: Any) -> str:
    db = getattr(dl, "db", None)
    if db is None:
        return "<unknown>"
    path = getattr(db, "db_path", None)
    return str(path) if path is not None else "<unknown>"


def emit_config_banner(dl: Any, poll_interval_s: int) -> None:
    """Print a simple configuration banner for the Sonic monitor."""
    db_path = _safe_db_path(dl)
    lines = [
        "══════════════════════════════════════════════════════════════",
        "   🦔 Sonic Monitor Configuration",
        "══════════════════════════════════════════════════════════════",
        f"   🕒 Poll Interval : {poll_interval_s}s",
        f"   🗄️  Database Path : {db_path}",
        "══════════════════════════════════════════════════════════════",
    ]
    for line in lines:
        print(line)
