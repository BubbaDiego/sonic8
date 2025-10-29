# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import logging
import os
import sys
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

def emit_config_banner(dl, interval: Optional[int] = None) -> None:
    # Banner has moved to sonic_reporting.banner_config
    return

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
    All detailed sections (prices, positions, hedges, notifications, sources) are rendered
    by sonic_reporting.* modules. We do not print them here.
    """
    print(f"✅ cycle #{loop_counter} done • {total_elapsed:.2f}s  (sleep {sleep_time:.1f}s)", flush=True)

# ----------------- JSONL summary (keep if used; safe to leave) -----------------
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

# ----------------- back-compat shims for legacy imports -----------------
def install_strict_console_filter(enable_color: bool = True) -> None:
    install_compact_console_filter(enable_color=enable_color)

def neuter_legacy_console_logger(level: int = logging.CRITICAL) -> None:
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
    if os.getenv("SONIC_FILTER_OFF", "0") == "1":
        return
    for src in ("ConsoleLogger","console_logger","LoggerControl","werkzeug","uvicorn.access","fuzzy_wuzzy","asyncio"):
        try:
            lg = logging.getLogger(src)
            lg.propagate = False
            for h in list(lg.handlers):
                lg.removeHandler(h)
            lg.handlers.clear()
            lg.setLevel(logging.ERROR)
        except Exception:
            pass
