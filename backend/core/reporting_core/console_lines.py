"""
console_lines.py — Legacy compatibility shim (signature-adapting)

Some parts of the codebase still import console rendering utilities from
`backend.core.reporting_core.console_lines`. The modern implementation lives
in `backend.core.reporting_core.console_reporter` and expects a richer call
signature for `emit_compact_cycle`.

This shim proxies legacy imports to the updated reporter and adapts older
call shapes (e.g., emit_compact_cycle(summary, cfg_for_endcap, interval, enable_color=True))
to the new signature so you do NOT need to touch callers like `sonic_monitor.py`.
"""

import logging
from typing import Any, Dict, List

# Try to import the modern reporter. If that fails, degrade gracefully so the app still runs.
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
    names: List[str] | None = None, *, level: int = logging.ERROR
) -> None:
    """Proxy to console_reporter.neuter_legacy_console_logger()."""
    if _REPORTER_OK:
        _neuter_legacy_console_logger(names, level=level)

def silence_legacy_console_loggers(
    names: List[str] | None = None, *, level: int = logging.ERROR
) -> None:
    """Back-compat alias expected by some builds; proxies to neuter_*."""
    if _REPORTER_OK:
        _silence_legacy_console_loggers(names, level=level)
    else:  # pragma: no cover
        neuter_legacy_console_logger(names, level=level)

def _derive_cycle_numbers(csum: Dict[str, Any], interval_hint: Any) -> Dict[str, Any]:
    """
    Best-effort derivation of numbers the new reporter expects when the caller
    used the legacy signature. We prefer values present in the summary.
    """
    durations = csum.get("durations_ms") or {}
    cyc_ms = int(durations.get("cyclone") or 0)
    total_ms = int(durations.get("total") or 0)
    total_elapsed = float(total_ms) / 1000.0 if total_ms else 0.0

    # loop counter often stored by the caller; fall back to 0
    loop_counter = int(csum.get("cycle") or csum.get("loop") or 0)

    # interval from hint or summary; sleep from summary or interval
    try:
        interval = int(interval_hint) if interval_hint is not None else int(csum.get("interval") or 0)
    except Exception:
        interval = int(csum.get("interval") or 0)

    try:
        sleep_time = float(csum.get("sleep_s") or interval or 0.0)
    except Exception:
        sleep_time = float(interval or 0.0)

    return {
        "cyc_ms": cyc_ms,
        "interval": interval,
        "loop_counter": loop_counter,
        "total_elapsed": total_elapsed,
        "sleep_time": sleep_time,
    }

def emit_compact_cycle(
    *args,
    **kwargs,
) -> None:
    """
    Signature-adapting proxy to console_reporter.emit_compact_cycle.

    New reporter signature:
        emit_compact_cycle(csum, cyc_ms, interval, loop_counter, total_elapsed, sleep_time, *, enable_color=False)

    Legacy call shapes seen in older code:
        emit_compact_cycle(summary, cfg_for_endcap, interval, enable_color=True)
        emit_compact_cycle(summary, interval)
    """
    if not _REPORTER_OK:
        # Minimal degraded path: print inline alerts + notifications if present.
        try:  # pragma: no cover
            csum = args[0] if args else {}
            alerts_inline = (csum.get("alerts") or {}).get("inline") or "—"
            notif = csum.get("notifications_brief", "NONE (no_breach)")
            print(f"   🔔 Alerts   : {alerts_inline}")
            print(f"   📨 Notifications : {notif}")
        except Exception:
            pass
        return

    # If caller already supplied the full new signature (≥7 positional args), just forward.
    if len(args) >= 7:
        _emit_compact_cycle(*args, **kwargs)
        return

    # Legacy/ad-hoc shapes: adapt them to the new signature.
    if not args:
        return  # nothing to do

    csum = args[0] if len(args) >= 1 else {}
    # legacy often passes (csum, cfg_for_endcap, interval, enable_color=?)
    interval_hint = None
    enable_color = bool(kwargs.get("enable_color", False))

    if len(args) >= 3:
        interval_hint = args[2]
    elif len(args) == 2:
        # sometimes only (csum, interval) was passed
        interval_hint = args[1]

    if "enable_color" in kwargs:
        enable_color = bool(kwargs["enable_color"])
    else:
        # legacy sometimes passed enable_color as 4th positional
        if len(args) >= 4:
            try:
                enable_color = bool(args[3])
            except Exception:
                enable_color = False

    nums = _derive_cycle_numbers(csum, interval_hint)
    _emit_compact_cycle(
        csum,
        nums["cyc_ms"],
        nums["interval"],
        nums["loop_counter"],
        nums["total_elapsed"],
        nums["sleep_time"],
        enable_color=enable_color,
    )

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
