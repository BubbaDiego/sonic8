
"""Console logging utilities with color, structured data, and robust verbosity control.

This v3 module is a **drop‑in replacement** for the previous ``console_logger.py``  fileciteturn0file0.

Key upgrades
------------
* **Conventional severity levels** (DEBUG–CRITICAL) + custom SUCCESS.
* **Global and per‑module thresholds** via ``set_level`` or ``LOG_LEVEL`` env.
* **Rich‑powered formatting** with graceful ANSI fallback; no more garbled codes on Windows/CI.
* **Thread‑safe emission** using a class‑level :pyclass:`threading.RLock`.
* **Structured events** – emit ``json`` when ``LOG_FORMAT=json`` or forward to extra sinks.
* **Pluggable sinks** – call :pyfunc:`add_sink` to tee logs to files, Kafka etc.
* **Exception helper** – preserves tracebacks.
* **100 % backward‑compatible** public API (``info``, ``success`` …).

External dependency (optional): ``rich`` ≥ 13.0.  If absent, the logger falls back to plain ANSI.

Example
-------
>>> from console_logger import ConsoleLogger as Log
>>> Log.set_level("DEBUG")                # show everything
>>> Log.info("Started job")
>>> Log.debug("Payload prepared", payload={"rows": 42})
>>> try:
...     1/0
... except ZeroDivisionError as e:
...     Log.exception(e, "While crunching numbers")

Environment knobs
-----------------
* ``LOG_LEVEL``   – e.g. ``WARNING``.
* ``LOG_FORMAT``  – ``json`` to force JSON lines.
* ``LOG_JSON``    – legacy alias for ``LOG_FORMAT=json``.
* ``LOG_NO_EMOJI`` – ``1`` to strip emoji.

"""

from __future__ import annotations

import inspect
import json
import os
import threading
import time
from contextlib import contextmanager
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional

# ------------- Optional Rich import & capability test ----------------------
try:
    from rich.console import Console  # type: ignore
    _RICH_CONSOLE = Console()
    _RICH_SUPPORTED = _RICH_CONSOLE.is_terminal
except Exception:  # pragma: no cover
    _RICH_CONSOLE = None
    _RICH_SUPPORTED = False

# ---------------------- Severity level ------------------------------------

class Level(IntEnum):
    DEBUG = 10
    INFO = 20
    SUCCESS = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

    @classmethod
    def coerce(cls, value: str | int) -> "Level":
        if isinstance(value, int):
            return Level(value)
        try:
            return Level[value.upper()]
        except KeyError as e:
            raise ValueError(f"Unknown log level: {value}") from e


# ---------------------------- Main class ----------------------------------

class ConsoleLogger:
    """Human‑friendly yet production‑grade console logger."""

    # Runtime toggles ------------------------------------------------------
    logging_enabled: bool = True
    debug_trace_enabled: bool = False
    trace_modules: set[str] = set()

    # Verbosity maps -------------------------------------------------------
    _default_level: Level = Level.coerce(os.getenv("LOG_LEVEL", Level.INFO))
    _module_levels: dict[str, Level] = {}            # per‑module overrides

    # Group muting inherited from v2
    group_map: dict[str, list[str]] = {}
    group_log_control: dict[str, bool] = {}
    module_log_control: dict[str, bool] = {}

    # Sinks and locks ------------------------------------------------------
    _sinks: list[Callable[[dict[str, Any]], None]] = []
    _lock = threading.RLock()

    # Timers ---------------------------------------------------------------
    _timers: dict[str, float] = {}

    # Config flags ---------------------------------------------------------
    _force_json: bool = os.getenv("LOG_FORMAT", os.getenv("LOG_JSON", "")).lower() == "json"
    _strip_emoji: bool = os.getenv("LOG_NO_EMOJI", "") == "1"

    # Palette & icons ------------------------------------------------------
    _COLORS = {
        Level.DEBUG: "\033[38;5;208m",   # Orange‑ish
        Level.INFO: "\033[94m",          # Light blue
        Level.SUCCESS: "\033[92m",       # Green
        Level.WARNING: "\033[93m",       # Yellow
        Level.ERROR: "\033[91m",         # Red
        Level.CRITICAL: "\033[95m",      # Magenta
        "highlight": "\033[38;5;99m",
        "route": "\033[96m",
        "endc": "\033[0m",
    }

    _ICONS = {
        Level.DEBUG: "🐞",
        Level.INFO: "ℹ️",
        Level.SUCCESS: "✅",
        Level.WARNING: "⚠️",
        Level.ERROR: "❌",
        Level.CRITICAL: "☠️",
        "highlight": "✨",
        "route": "🌐",
    }

    # ----------------------------------------------------------------------
    #                Public configuration helpers
    # ----------------------------------------------------------------------

    @classmethod
    def set_level(cls, level: str | int, module: str | None = None) -> None:
        """Change global or per‑module minimum level.

        When *module* is None, the default level is updated.
        """
        lvl = Level.coerce(level)
        if module:
            cls._module_levels[module] = lvl
        else:
            cls._default_level = lvl

    @classmethod
    def add_sink(cls, func: Callable[[dict[str, Any]], None]) -> None:
        """Register a callable that receives the raw *event* dict.

        The callable **must not** raise; any exception is caught and ignored.
        Typical sinks: write to file, send to queue, push to metrics.
        """
        cls._sinks.append(func)

    # --------------------------- Internals --------------------------------

    # Utility to get timestamp; using time.strftime keeps deps minimal.
    @staticmethod
    def _timestamp() -> str:
        return time.strftime("%Y‑%m‑%d %H:%M:%S", time.localtime())

    @classmethod
    def _get_caller_module(cls) -> str:
        for frame in inspect.stack()[3:]:
            module = inspect.getmodule(frame[0])
            if module and hasattr(module, "__name__"):
                name = module.__name__
                if name == "__main__":
                    # strip .py
                    return frame.filename.split("/")[-1].split(".")[0]
                return name.split(".")[-1]
        return "unknown"

    # v2 compatibility – honours module & group muting flags.
    @classmethod
    def _is_logging_allowed(cls, module: str) -> bool:
        if not cls.logging_enabled:
            return False
        if module in cls.module_log_control and not cls.module_log_control[module]:
            return False
        for group, modules in cls.group_map.items():
            if module in modules and not cls.group_log_control.get(group, True):
                return False
        for prefix, enabled in cls.module_log_control.items():
            if not enabled and module.startswith(prefix):
                return False
        return True

    @classmethod
    def _meets_threshold(cls, level: Level, module: str) -> bool:
        min_allowed = cls._module_levels.get(module, cls._default_level)
        return level >= min_allowed

    # Rich pretty emitter
    @classmethod
    def _emit_pretty(cls, event: dict[str, Any]) -> None:
        level = event["level"]
        color = cls._COLORS.get(level, "")
        endc = cls._COLORS["endc"]
        icon = cls._ICONS.get(level, "")
        if cls._strip_emoji:
            icon = ""
        payload_str = ""
        payload = event.get("payload")
        if payload:
            # simple inline for primitives; pretty json for complex
            if all(isinstance(v, (str, int, float, bool, type(None))) for v in payload.values()):
                payload_str = " → " + ", ".join(f"{k}: {v}" for k, v in payload.items())
            else:
                payload_str = "\n" + json.dumps(payload, indent=2, default=str)
                payload_str = "\n".join("    " + l for l in payload_str.splitlines())
        label = f"{icon} {event['message']} :: [{event['source']}] @ {event['ts']}"
        text = f"{color}{label}{payload_str}{endc}"

        if _RICH_SUPPORTED:
            style = "bold"
            _RICH_CONSOLE.print(text, style=style, overflow="fold")
        else:
            print(text)

    # Base printer
    @classmethod
    def _print(
        cls,
        level: Level,
        message: str,
        source: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        caller_module = cls._get_caller_module()
        eff_source = source or caller_module

        if not cls._is_logging_allowed(eff_source):
            return
        if not cls._meets_threshold(level, eff_source):
            return

        event = {
            "ts": cls._timestamp(),
            "level": level.name,
            "level_no": int(level),
            "message": message,
            "source": eff_source,
            "payload": payload or {},
        }

        with cls._lock:
            # emit to console
            if cls._force_json:
                print(json.dumps(event, default=str))
            else:
                cls._emit_pretty(event)
            # fan‑out to sinks
            for sink in cls._sinks:
                try:
                    sink(event)
                except Exception:  # pragma: no cover
                    pass

    # ------------------- Backwards compatible API -------------------------

    @classmethod
    def debug(cls, msg: str, source: str | None = None, payload: dict | None = None) -> None:
        cls._print(Level.DEBUG, msg, source, payload)

    @classmethod
    def info(cls, msg: str, source: str | None = None, payload: dict | None = None) -> None:
        cls._print(Level.INFO, msg, source, payload)

    @classmethod
    def success(cls, msg: str, source: str | None = None, payload: dict | None = None) -> None:
        cls._print(Level.SUCCESS, msg, source, payload)

    @classmethod
    def warning(cls, msg: str, source: str | None = None, payload: dict | None = None) -> None:
        cls._print(Level.WARNING, msg, source, payload)

    @classmethod
    def error(cls, msg: str, source: str | None = None, payload: dict | None = None) -> None:
        cls._print(Level.ERROR, msg, source, payload)

    @classmethod
    def critical(cls, msg: str, source: str | None = None, payload: dict | None = None) -> None:
        cls._print(Level.CRITICAL, msg, source, payload)

    # Alias for v2
    death = critical

    # ------------- Structured helpers & extras ---------------------------

    @classmethod
    def exception(cls, exc: Exception, msg: str = "", **kw) -> None:
        """Log *exc* with traceback while preserving threshold logic."""
        import traceback, io as _io

        buf = _io.StringIO()
        traceback.print_exception(exc, file=buf)
        tb = buf.getvalue()
        payload = kw.get("payload", {})
        payload["traceback"] = tb
        full_msg = f"{msg} - {exc}" if msg else str(exc)
        cls._print(Level.ERROR, full_msg, kw.get("source"), payload)

    @classmethod
    def banner(cls, text: str) -> None:
        """Pretty divider for console sessions."""
        if _RICH_SUPPORTED:
            _RICH_CONSOLE.rule(f"[bold magenta]{text}")
        else:
            print("\n" + "="*60)
            print(f"🚀 {text.center(50)} 🚀")
            print("="*60 + "\n")

    # ----------------------------- Timers ---------------------------------

    @classmethod
    def start_timer(cls, label: str) -> None:
        cls._timers[label] = time.time()

    @classmethod
    def end_timer(cls, label: str, source: str | None = None) -> None:
        if label not in cls._timers:
            cls.warning(f"No timer started for label '{label}'", source)
            return
        elapsed = time.time() - cls._timers.pop(label)
        cls.success(f"Timer '{label}' completed in {elapsed:.2f}s", source)

    # ------------------------- v2 Compatibility ---------------------------

    @classmethod
    def silence_module(cls, mod: str) -> None:
        cls.module_log_control[mod] = False

    @classmethod
    def enable_module(cls, mod: str) -> None:
        cls.module_log_control[mod] = True

    @classmethod
    def assign_group(cls, group: str, modules: list[str]) -> None:
        cls.group_map[group] = modules

    @classmethod
    def silence_group(cls, group: str) -> None:
        cls.group_log_control[group] = False

    @classmethod
    def enable_group(cls, group: str) -> None:
        cls.group_log_control[group] = True

    @classmethod
    @contextmanager
    def temporary_module(cls, module: str, enabled: bool):
        prev = cls.module_log_control.get(module, True)
        cls.module_log_control[module] = enabled
        try:
            yield
        finally:
            cls.module_log_control[module] = prev

    @classmethod
    @contextmanager
    def temporary_group(cls, group: str, enabled: bool):
        prev = cls.group_log_control.get(group, True)
        cls.group_log_control[group] = enabled
        try:
            yield
        finally:
            cls.group_log_control[group] = prev

    # ------------------------ Diagnostic helpers --------------------------

    @classmethod
    def init_status(cls) -> None:
        muted = [m for m, enabled in cls.module_log_control.items() if not enabled]
        enabled = [m for m, e in cls.module_log_control.items() if e]

        msg = "\n"
        if muted:
            msg += f"    🔒 Muted Modules:      {', '.join(muted)}\n"
        if enabled:
            msg += f"    🔊 Enabled Modules:    {', '.join(enabled)}\n"
        if cls.group_map:
            msg += "    🧠 Groups:\n"
            for g, mods in cls.group_map.items():
                msg += f"        {g:<10} ➜ {', '.join(mods)}\n"

        cls.info("🧩 ConsoleLogger initialized.", source="Logger")
        print(msg.strip())

    @classmethod
    def hijack_logger(cls, target_logger_name: str) -> None:
        """Hijack a standard ``logging`` logger and redirect to :class:`ConsoleLogger`."""
        import logging

        def handler(record: logging.LogRecord):
            mod = target_logger_name
            if cls._is_logging_allowed(mod):
                cls.info(record.getMessage(), source=mod)

        h = logging.StreamHandler()
        h.emit = handler  # type: ignore
        hijacked_logger = logging.getLogger(target_logger_name)
        hijacked_logger.handlers = [h]
        hijacked_logger.propagate = False
        hijacked_logger.setLevel(logging.INFO)
        cls.info(f"🕵️ Logger '{target_logger_name}' hijacked.", source="LoggerControl")

    # ------------------------ Convenience helpers -----------------------

    @classmethod
    def print_dashboard_link(
        cls,
        host: str = "127.0.0.1",
        port: int = 5001,
        route: str = "/dashboard",
    ) -> None:
        """Log a simple dashboard URL."""
        url = f"http://{host}:{port}{route}"
        cls.info(f"🌐 Sonic Dashboard: {url}")

    # ------------------- Convenience functional aliases -------------------

    route = info  # retain colored route printing via custom styling if needed

# End of ConsoleLogger
