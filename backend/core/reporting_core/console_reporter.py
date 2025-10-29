# -*- coding: utf-8 -*-
from __future__ import annotations
import json, logging, os, sys, time
from pathlib import Path
from typing import Any, Dict, Optional


# ----------------- logging filter & stdout wrapper -----------------
def install_compact_console_filter(enable_color: bool = True) -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    for name in ("ConsoleLogger", "console_logger", "LoggerControl", "werkzeug",
                 "uvicorn.access", "fuzzy_wuzzy", "asyncio"):
        logging.getLogger(name).setLevel(logging.ERROR)

    class _DropXCOM(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            try:
                msg = record.getMessage() or ""
            except Exception:
                msg = ""
            name = (record.name or "").lower()
            if "xcom" in name and record.levelno <= logging.INFO:
                return False
            if msg.startswith("DEBUG[XCOM]"):
                return False
            return True
    root.addFilter(_DropXCOM())

    class _StdoutFilter:
        def __init__(self, stream):
            self._s = stream
        def write(self, s):
            if "DEBUG[XCOM]" in str(s):
                return
            self._s.write(s)
        def flush(self):
            try: self._s.flush()
            except Exception: pass
        def isatty(self):
            return getattr(self._s, "isatty", lambda: False)()
    if not isinstance(sys.stdout, _StdoutFilter):
        sys.stdout = _StdoutFilter(sys.stdout)
    if not isinstance(sys.stderr, _StdoutFilter):
        sys.stderr = _StdoutFilter(sys.stderr)

# --- backward-compat alias (older callers expect this name) -------------------
def install_strict_console_filter(enable_color: bool = True) -> None:
    """
    Alias for historical name. Delegates to install_compact_console_filter.
    """
    install_compact_console_filter(enable_color=enable_color)


# ----------------- no-op banner (your new banner lives elsewhere) -----------------
def emit_config_banner(dl, interval: Optional[int] = None) -> None:
    return  # banner now handled by sonic_reporting.banner_config


# ----------------- compact cycle (end-of-cycle line only) -----------------
def emit_compact_cycle(
    csum: Dict[str, Any],
    cyc_ms: int,
    interval: int,
    loop_counter: int,
    total_elapsed: float,
    sleep_time: float,
    db_basename: str | None = None,
) -> None:
    """
    Prints only the succinct end-of-cycle line.
    All detailed sections (prices, positions, hedges, notifications) are rendered
    by sonic_reporting.* modules, so we do NOT print them here.
    """
    print(f"✅ cycle #{loop_counter} done • {total_elapsed:.2f}s  (sleep {sleep_time:.1f}s)", flush=True)


# ----------------- JSONL summary (kept for parity, safe to no-op if not used) -----------------
def emit_json_summary(
    csum: Dict[str, Any],
    cyc_ms: int,
    loop_counter: int,
    total_elapsed: float,
    sleep_time: float,
) -> None:
    try:
        out = dict(csum or {})
        out.setdefault("durations", {})["cyclone_ms"] = cyc_ms
        out["loop_counter"] = loop_counter
        out["elapsed_s"] = total_elapsed
        out["sleep_s"] = sleep_time
        logs_dir = Path(__file__).resolve().parents[3] / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "sonic_summary.jsonl").open("a", encoding="utf-8").write(json.dumps(out) + "\n")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Back-compat shims for older callers
# ---------------------------------------------------------------------------
def install_strict_console_filter(enable_color: bool = True) -> None:
    """
    Older code calls this; delegate to the new compact filter.
    """
    install_compact_console_filter(enable_color=enable_color)

def neuter_legacy_console_logger(level: int = logging.CRITICAL) -> None:
    """
    Older code calls this to silence the old console loggers.
    We aggressively mute the legacy loggers and common noisy modules.
    """
    for name in ("ConsoleLogger", "console_logger", "LoggerControl"):
        try:
            lg = logging.getLogger(name)
            lg.handlers[:] = []
            lg.propagate = False
            lg.setLevel(level)
        except Exception:
            pass
    # keep access logs quiet too (matches your banner's muted modules)
    try:
        logging.getLogger("uvicorn.access").setLevel(logging.ERROR)
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Back-compat shims for older callers
# ---------------------------------------------------------------------------
import logging
import os

def install_strict_console_filter(enable_color: bool = True) -> None:
    """
    Older code calls this; delegate to the new compact filter.
    """
    install_compact_console_filter(enable_color=enable_color)

def neuter_legacy_console_logger(level: int = logging.CRITICAL) -> None:
    """
    Older code calls this to silence the old console loggers.
    We aggressively mute the legacy loggers and common noisy modules.
    """
    for name in ("ConsoleLogger", "console_logger", "LoggerControl"):
        try:
            lg = logging.getLogger(name)
            lg.handlers[:] = []
            lg.propagate = False
            lg.setLevel(level)
        except Exception:
            pass
    try:
        logging.getLogger("uvicorn.access").setLevel(logging.ERROR)
    except Exception:
        pass

def silence_legacy_console_loggers() -> None:
    """
    Sonic6-era helper: block legacy/noisy loggers globally.
    Behavior parity with prior version:
      - remove handlers
      - stop propagation
      - set level to ERROR
    """
    if os.getenv("SONIC_FILTER_OFF", "0") == "1":
        return
    for src in (
        "ConsoleLogger",
        "console_logger",
        "LoggerControl",
        "werkzeug",
        "uvicorn.access",
        "fuzzy_wuzzy",
        "asyncio",
    ):
        try:
            lg = logging.getLogger(src)
            lg.propagate = False
            for h in list(lg.handlers):
                lg.removeHandler(h)
            lg.handlers.clear()
            lg.setLevel(logging.ERROR)
        except Exception:
            pass
