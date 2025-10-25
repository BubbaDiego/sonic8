"""
console_lines.py — Legacy compatibility shim

Some parts of the codebase still import console rendering utilities from
`backend.core.reporting_core.console_lines`. The modern implementation lives
in `backend.core.reporting_core.console_reporter`.

This module proxies legacy imports to the updated reporter so callers like
`sonic_monitor.py` do not need to change.
"""

import logging
from typing import Any, Dict, List, Optional

# Try to import the modern reporter. If that fails (partial checkout etc.),
# we degrade gracefully so the app can still run.
try:
    from backend.core.reporting_core.console_reporter import (  # type: ignore
        StrictWhitelistFilter as _StrictWhitelistFilter,
        install_strict_console_filter as _install_strict_console_filter,
        neuter_legacy_console_logger as _neuter_legacy_console_logger,
        silence_legacy_console_loggers as _silence_legacy_console_loggers,
        emit_compact_cycle as _emit_compact_cycle,
        emit_sources_line as _emit_sources_line,
        emit_json_summary as _emit_json_summary,
    )
    _REPORTER_OK = True
except Exception as _e:  # pragma: no cover
    _REPORTER_OK = False
    _IMPORT_ERR = _e
    logging.getLogger("ConsoleReporter").warning(
        "console_lines shim: failed to import console_reporter (%s). "
        "Falling back to minimal no-op stubs.", type(_e).__name__
    )

# ---------------------------- Public API (proxies) ----------------------------

def StrictWhitelistFilter(*names: str):
    """Proxy to console_reporter.StrictWhitelistFilter."""
    if _REPORTER_OK:
        return _StrictWhitelistFilter(*names)
    # Minimal permissive filter if reporter unavailable
    class _Permissive(logging.Filter):  # pragma: no cover
        def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
            return True
    return _Permissive()

def install_strict_console_filter() -> None:
    """Proxy to console_reporter.install_strict_console_filter()."""
    if _REPORTER_OK:
        _install_strict_console_filter()

def neuter_legacy_console_logger(
    names: Optional[List[str]] = None, *, level: int = logging.ERROR
) -> None:
    """Proxy to console_reporter.neuter_legacy_console_logger()."""
    if _REPORTER_OK:
        _neuter_legacy_console_logger(names, level=level)

def silence_legacy_console_loggers(
    names: Optional[List[str]] = None, *, level: int = logging.ERROR
) -> None:
    """Back-compat alias expected by some builds; proxies to neuter_*."""
    if _REPORTER_OK:
        _silence_legacy_console_loggers(names, level=level)
    else:  # pragma: no cover
        neuter_legacy_console_logger(names, level=level)

def emit_compact_cycle(
    csum: Dict[str, Any],
    cyc_ms: int,
    interval: int,
    loop_counter: int,
    total_elapsed: float,
    sleep_time: float,
    *,
    enable_color: bool = False,
) -> None:
    """
    Proxy to console_reporter.emit_compact_cycle(), which renders the compact
    cycle summary with a BLUE, aligned 'Alerts' header and one line per monitor.
    """
    if _REPORTER_OK:
        _emit_compact_cycle(
            csum, cyc_ms, interval, loop_counter, total_elapsed, sleep_time,
            enable_color=enable_color
        )
        return
    # Minimal degraded path if reporter not available (single-line fallback).
    try:  # pragma: no cover
        alerts_inline = (csum.get("alerts") or {}).get("inline") or "—"
        notif = csum.get("notifications_brief", "NONE (no_breach)")
        print(f"   🔔 Alerts   : {alerts_inline}")
        print(f"   📨 Notifications : {notif}")
    except Exception:
        pass

def emit_sources_line(sources: Dict[str, Any], label: str = "") -> None:
    """Proxy to console_reporter.emit_sources_line()."""
    if _REPORTER_OK:
        _emit_sources_line(sources, label=label)

def emit_json_summary(
    csum: Dict[str, Any],
    cyc_ms: int,
    loop_counter: int,
    total_elapsed: float,
    sleep_time: float,
) -> None:
    """Proxy to console_reporter.emit_json_summary()."""
    if _REPORTER_OK:
        _emit_json_summary(csum, cyc_ms, loop_counter, total_elapsed, sleep_time)

__all__ = [
    "StrictWhitelistFilter",
    "install_strict_console_filter",
    "neuter_legacy_console_logger",
    "silence_legacy_console_loggers",
    "emit_compact_cycle",
    "emit_sources_line",
    "emit_json_summary",
]
