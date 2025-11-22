# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib, os, sys, json, logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.core.core_constants import SONIC_MONITOR_CONFIG_PATH  # NEW
from backend.core.reporting_core.sonic_reporting.console_panels.theming import (
    get_panel_order,
    is_enabled,
)

logger = logging.getLogger("sonic.engine")

# Follow the same dynamic config path as the engine / API
MON_CFG_PATH = SONIC_MONITOR_CONFIG_PATH


def _load_monitor_cfg():
    try:
        with MON_CFG_PATH.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
        logger.debug("[resolve] cfg path: %s", MON_CFG_PATH)
        return cfg, str(MON_CFG_PATH)
    except Exception as e:
        logger.debug("[resolve] cfg load failed: %s", e)
        return {}, "<unknown>"


# ---- Panel module order (override with SONIC_REPORT_PANELS) -------------------
DEFAULT_PANEL_MODULES: List[str] = [
   # "backend.core.reporting_core.sonic_reporting.console_panels.preflight_config_panel",
    "backend.core.reporting_core.sonic_reporting.console_panels.price_panel",
    "backend.core.reporting_core.sonic_reporting.console_panels.positions_panel",
    "backend.core.reporting_core.sonic_reporting.console_panels.risk_panel",
    "backend.core.reporting_core.sonic_reporting.console_panels.monitor_panel",
    "backend.core.reporting_core.sonic_reporting.console_panels.blast_panel",
    "backend.core.reporting_core.sonic_reporting.console_panels.market_panel",
    "backend.core.reporting_core.sonic_reporting.console_panels.xcom_panel",
    # NOTE:
    #   The 🎯 Session / Goals panel is rendered separately after the Wallets
    #   panel in monitor_core.sonic.reporting.console.runner.run_console_reporters().
   # "backend.core.reporting_core.sonic_reporting.console_panels.resolve_log_panel",
]

# Back-compat symbol; some code may import PANEL_MODULES at import-time.
PANEL_MODULES: List[str] = list(DEFAULT_PANEL_MODULES)


def _get_panel_modules() -> List[str]:
    env = os.environ.get("SONIC_REPORT_PANELS", "").strip()
    if env:
        return [m.strip() for m in env.split(",") if m.strip()]
    return list(DEFAULT_PANEL_MODULES)


# ---- width + small utils ------------------------------------------------------
def _console_width(default: int = 92) -> int:
    try:
        return max(60, min(180, int(os.environ.get("SONIC_CONSOLE_WIDTH", default))))
    except Exception:
        return default


def _normalize_lines(obj: Any) -> List[str]:
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, tuple):
        return list(obj)
    if isinstance(obj, str):
        return [obj]
    try:
        return list(obj)
    except Exception:
        return [str(obj)]


# ---- Panels runner ------------------------------------------------------------
def render_panel_stack(
    *,
    ctx: Dict[str, Any],
    dl=None,
    cfg: Optional[Dict[str, Any]] = None,
    width: Optional[int] = None,
    writer=print,
) -> List[str]:
    width = width or _console_width()
    ctx = dict(ctx or {})

    loaded_cfg, cfg_path_hint = _load_monitor_cfg()
    if isinstance(cfg, dict):
        cfg_dict = cfg
    else:
        cfg_dict = loaded_cfg

    if not isinstance(cfg_dict, dict):
        cfg_dict = {}

    ctx.setdefault("dl", dl)
    ctx.setdefault("cfg_path_hint", cfg_path_hint)
    ctx["cfg"] = cfg_dict
    ctx.setdefault("width", width)
    ctx.setdefault("resolve_traces", [])

    modules = _get_panel_modules()
    all_lines: List[str] = []
    panel_entries: List[Tuple[str, Any, int]] = []

    for idx, mod_path in enumerate(modules):
        if (
            mod_path.endswith(".market_panel")
            and ".console_panels." not in mod_path
        ):
            # Old inline market panel renderers are deprecated; skip them so
            # Market Alerts is only rendered once via console_panels.market_panel.
            continue
        try:
            mod = importlib.import_module(mod_path)
        except Exception as exc:
            logger.error(
                "Failed to import panel module %s: %s",
                mod_path,
                exc,
                exc_info=True,
            )
            continue

        name = getattr(mod, "__name__", mod_path).split(".")[-1]
        base = name.replace("_panel", "")
        if base == "price":
            slug = "prices"
        elif base == "positions":
            slug = "positions"
        elif base == "risk":
            slug = "risk"
        elif base == "monitor":
            slug = "monitors"
        elif base == "blast":
            slug = "blast"
        elif base == "market":
            slug = "market"
        elif base == "xcom":
            slug = "xcom"
        elif base == "wallets":
            slug = "wallets"
        elif base == "preflight_config":
            slug = "preflight"
        elif base == "activity":
            slug = "activity"
        elif base == "session":
            slug = "session"
        else:
            slug = base

        panel_entries.append((slug, mod, idx))

    env_panels = os.environ.get("SONIC_REPORT_PANELS", "").strip()
    if env_panels:
        ordered_entries = panel_entries
    else:
        desired_order = get_panel_order()
        index_map = {slug: i for i, slug in enumerate(desired_order)}

        def _sort_key(entry: Tuple[str, Any, int]) -> Tuple[int, int]:
            slug, _mod, orig_idx = entry
            return (index_map.get(slug, len(desired_order) + orig_idx), orig_idx)

        ordered_entries = sorted(panel_entries, key=_sort_key)

    for slug, mod, _ in ordered_entries:
        if not is_enabled(slug):
            continue

        mod_path = getattr(mod, "__name__", "<unknown>")
        try:
            # prefer connector(dl, ctx, width); fallback to render(ctx, width=…)
            lines_obj = None
            if hasattr(mod, "connector") and callable(getattr(mod, "connector")):
                try:
                    lines_obj = mod.connector(dl, ctx, width)
                except TypeError:
                    lines_obj = mod.connector(ctx)
            elif hasattr(mod, "render") and callable(getattr(mod, "render")):
                try:
                    lines_obj = mod.render(ctx, width=width)
                except TypeError:
                    lines_obj = mod.render(ctx)

            out = _normalize_lines(lines_obj)
            for ln in out:
                writer(ln)
            all_lines.extend(out)

        except Exception as e:
            msg = f"[REPORT] {mod_path}.render failed: {e}"
            writer(msg)
            all_lines.append(msg)

    return all_lines


# ---- public entry used by monitor after compact lines -------------------------
def emit_full_console(*, loop_counter: int, poll_interval_s: int, total_elapsed_s: float, ts: Any, dl=None, width: Optional[int] = None, writer=print) -> None:
    cfg, cfg_path_hint = _load_monitor_cfg()
    ctx = {
        "loop_counter": int(loop_counter),
        "poll_interval_s": int(poll_interval_s),
        "total_elapsed_s": float(total_elapsed_s),
        "ts": ts,
        "dl": dl,
        "cfg": cfg,
        "cfg_path_hint": cfg_path_hint,
    }
    render_panel_stack(ctx=ctx, dl=dl, cfg=cfg, width=width or _console_width(), writer=writer)


# ────────────────────────────────────────────────────────────────────────────────
# Logging filter & stdout wrapper
# ────────────────────────────────────────────────────────────────────────────────

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
    # Banner moved to sonic_reporting.console_panels.banner_panel
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
