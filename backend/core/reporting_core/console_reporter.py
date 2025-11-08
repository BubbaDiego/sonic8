# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ────────────────────────────────────────────────────────────────────────────────
# Panel configuration (order & overrides)
#   • Default order below; can be overridden via env SONIC_REPORT_PANELS
#     as a comma-separated list of module paths.
# ────────────────────────────────────────────────────────────────────────────────

DEFAULT_PANEL_MODULES: List[str] = [
    "backend.core.reporting_core.sonic_reporting.positions_panel",
    "backend.core.reporting_core.sonic_reporting.price_panel",
    "backend.core.reporting_core.sonic_reporting.xcom_panel",
    "backend.core.reporting_core.sonic_reporting.wallets_panel",
    "backend.core.reporting_core.sonic_reporting.raydium_panel",
    "backend.core.reporting_core.sonic_reporting.cycle_footer_panel",  # ← last
]

# Back-compat symbol; some code may import PANEL_MODULES at import-time.
PANEL_MODULES: List[str] = list(DEFAULT_PANEL_MODULES)


def _get_panel_modules() -> List[str]:
    override = os.environ.get("SONIC_REPORT_PANELS", "").strip()
    if override:
        mods = [m.strip() for m in override.split(",") if m.strip()]
        if mods:
            return mods
    return list(DEFAULT_PANEL_MODULES)


# ────────────────────────────────────────────────────────────────────────────────
# Console style knobs (centralized here)
#   • SONIC_CONSOLE_WIDTH: console width (default 92)
#   • SONIC_FOOTER_RICH:   1/0 to use Rich for the footer panel (default ON)
#   • SONIC_FOOTER_BORDER: ANSI code for footer box border when not using Rich
#                          (default "38;5;39" = bright cyan)
# These are read by panels (e.g., cycle_footer_panel) via os.environ.
# ────────────────────────────────────────────────────────────────────────────────

def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return str(val).lower() in ("1", "true", "yes", "on")

def _init_console_style_defaults() -> None:
    # Default to Rich footer unless explicitly disabled.
    os.environ.setdefault("SONIC_FOOTER_RICH", "1")
    # Nice cyan-ish border for ANSI fallback.
    os.environ.setdefault("SONIC_FOOTER_BORDER", "38;5;39")
    # Width default (panels also read this).
    os.environ.setdefault("SONIC_CONSOLE_WIDTH", "92")


def _console_width(default: int = 92) -> int:
    try:
        return max(60, min(180, int(os.environ.get("SONIC_CONSOLE_WIDTH", default))))
    except Exception:
        return default


def _write_line(writer, line: str, *, flush: bool = False) -> None:
    if writer is print:
        print(line, flush=flush)
        return
    writer(line)
    if flush:
        flush_fn = getattr(writer, "flush", None)
        if callable(flush_fn):
            try:
                flush_fn()
            except Exception:
                pass


def _normalize_lines(obj: Any) -> List[str]:
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, tuple):
        return list(obj)
    if isinstance(obj, str):
        return [obj]
    # last-resort coercion
    try:
        return list(obj)
    except Exception:
        return [str(obj)]


# ────────────────────────────────────────────────────────────────────────────────
# Panel runner
# ────────────────────────────────────────────────────────────────────────────────

def render_panel_stack(
    dl=None,
    csum: Optional[Dict[str, Any]] = None,
    width: Optional[int] = None,
    writer=print,
) -> List[str]:
    """
    Import each panel and render it safely.
    Preference order: panel.connector(dl, ctx, width) → panel.render(ctx, width=...)
    Non-fatal on errors; prints a diagnostic line and continues.
    Returns the concatenated list of lines.
    """
    width = width or _console_width()
    summary = csum or {}
    ctx = {"dl": dl, "csum": summary, "summary": summary, "width": width}
    all_lines: List[str] = []

    modules = _get_panel_modules()
    for mod_path in modules:
        try:
            mod = importlib.import_module(mod_path)

            lines_obj = None
            # Prefer connector(dl, ctx, width) if available.
            fn_conn = getattr(mod, "connector", None)
            if callable(fn_conn):
                try:
                    lines_obj = fn_conn(dl, ctx, width)
                except TypeError:
                    # Older connectors may accept just (ctx)
                    lines_obj = fn_conn(ctx)

            if lines_obj is None:
                # Fall back to render(ctx, width=width)
                fn_r = getattr(mod, "render", None)
                if not callable(fn_r):
                    raise AttributeError("no render/connector")
                try:
                    lines_obj = fn_r(ctx, width=width)
                except TypeError:
                    lines_obj = fn_r(ctx)

            seq = _normalize_lines(lines_obj)
            for ln in seq:
                _write_line(writer, ln)
            all_lines.extend(seq)

        except Exception as e:
            msg = f"[REPORT] {mod_path}.render failed: {e}"
            _write_line(writer, msg)
            all_lines.append(msg)

    return all_lines


# ────────────────────────────────────────────────────────────────────────────────
# Logging filter & stdout wrapper
# ────────────────────────────────────────────────────────────────────────────────

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
            try:
                self._s.flush()
            except Exception:
                pass
        def isatty(self):
            return getattr(self._s, "isatty", lambda: False)()

    if not isinstance(sys.stdout, _StdoutFilter):
        sys.stdout = _StdoutFilter(sys.stdout)
    if not isinstance(sys.stderr, _StdoutFilter):
        sys.stderr = _StdoutFilter(sys.stderr)


def emit_config_banner(dl, interval: Optional[int] = None) -> None:
    # Banner moved to sonic_reporting.banner_panel
    return


# ────────────────────────────────────────────────────────────────────────────────
# Compact cycle line (top-of-cycle summary)
# ────────────────────────────────────────────────────────────────────────────────

def emit_compact_cycle(
    csum: Dict[str, Any],
    cyc_ms: int,
    interval: int,
    loop_counter: int,
    total_elapsed: float,
    sleep_time: float,
    db_basename: str | None = None,
    *,
    writer=print,
) -> None:
    """
    Prints only the succinct end-of-cycle line.
    All details (prices, positions, hedges, notifications, sources) are rendered
    by sonic_reporting.* modules. We do not print them here.
    """
    line = f"✅ cycle #{loop_counter} done • {total_elapsed:.2f}s  (sleep {sleep_time:.1f}s)"
    _write_line(writer, line, flush=True)


# ────────────────────────────────────────────────────────────────────────────────
# Full console (compact line + panels)
# ────────────────────────────────────────────────────────────────────────────────

def emit_full_console(
    csum: Dict[str, Any],
    cyc_ms: int,
    interval: int,
    loop_counter: int,
    total_elapsed: float,
    sleep_time: float,
    db_basename: str | None = None,
    *,
    dl=None,
    width: Optional[int] = None,
    writer=print,
) -> None:
    """
    Prints the compact cycle output, then all panels in order.
    Style knobs default here (Rich footer ON; ANSI fallback available).
    """
    # Ensure style defaults (Rich for footer, border color, width)
    _init_console_style_defaults()

    emit_compact_cycle(
        csum,
        cyc_ms,
        interval,
        loop_counter,
        total_elapsed,
        sleep_time,
        db_basename=db_basename,
        writer=writer,
    )
    render_panel_stack(dl=dl, csum=csum, width=width or _console_width(), writer=writer)


# ────────────────────────────────────────────────────────────────────────────────
# JSONL summary (unchanged/optional)
# ────────────────────────────────────────────────────────────────────────────────

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


# ────────────────────────────────────────────────────────────────────────────────
# Back-compat shims for legacy imports
# ────────────────────────────────────────────────────────────────────────────────

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


# --- legacy 'sources' printer (no-op) -----------------------------------------
def emit_sources_line(*args, **kwargs) -> None:
    """Back-compat: some old code calls this. We intentionally print nothing."""
    return
