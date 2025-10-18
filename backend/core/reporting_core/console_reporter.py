from __future__ import annotations

import logging
import os
from typing import Any, Dict, Iterable

# ---- Strict allowlist filter -------------------------------------------------

WL_SOURCES = {
    s.strip()
    for s in os.getenv(
        "SONIC_COMPACT_WHITELIST",
        "SonicMonitor,ConsoleReporter,XComCore,backend.core.xcom_core,backend.core.xcom,xcom_core,xcom",
    ).split(",")
    if s.strip()
}
WL_PREFIXES: tuple[str, ...] = ("backend.core.xcom", "xcom")

class StrictWhitelistFilter(logging.Filter):
    """Allow INFO/DEBUG only from sources we explicitly trust. Always pass WARNING+."""
    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        level = record.levelno
        if level >= logging.WARNING:
            return True
        src = getattr(record, "source", None) or record.name or ""
        if src in WL_SOURCES:
            return True
        return any(src.startswith(p) for p in WL_PREFIXES)

def install_strict_console_filter() -> None:
    """Attach the StrictWhitelistFilter to all console handlers and raise root to WARNING."""
    filt = StrictWhitelistFilter()
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=logging.WARNING)
    for logger_name in ("",):  # root only; propagate takes care of children
        logger = logging.getLogger(logger_name)
        for h in getattr(logger, "handlers", []):
            if isinstance(h, logging.StreamHandler):
                try:
                    h.addFilter(filt)
                except Exception:
                    pass
    root.setLevel(logging.WARNING)

# ---- Legacy/Noisy logger silencer --------------------------------------------

DEFAULT_BLOCKLIST = [
    "ConsoleLogger","console_logger","LoggerControl",
    "werkzeug","uvicorn.access","fuzzy_wuzzy","asyncio",
]


def _iter_blocklist() -> Iterable[str]:
    env_list = [x.strip() for x in os.getenv("SONIC_LOG_BLOCKLIST", "").split(",") if x.strip()]
    blocklist = list(env_list or DEFAULT_BLOCKLIST)
    if os.getenv("SONIC_CONSOLE_LOGGER", "").strip().lower() in {"1", "true", "on", "yes"}:
        blocklist = [
            name
            for name in blocklist
            if name not in {"ConsoleLogger", "console_logger", "LoggerControl"}
        ]
    return blocklist

def silence_legacy_console_loggers() -> list[str]:
    """Force-raise blocklisted loggers to ERROR and strip their StreamHandlers."""
    muted: list[str] = []
    for name in _iter_blocklist():
        try:
            lg = logging.getLogger(name)
            lg.setLevel(logging.ERROR)
            # remove direct console spew
            for h in list(getattr(lg, "handlers", [])):
                if isinstance(h, logging.StreamHandler):
                    try:
                        lg.removeHandler(h)
                    except Exception:
                        pass
            muted.append(name)
        except Exception:
            pass
    return muted


def neuter_legacy_console_logger() -> dict[str, Any]:
    """Force-mute the legacy ConsoleLogger regardless of import order or dotenv timing.

    Returns a small report of what was patched.
    """

    if os.getenv("SONIC_CONSOLE_LOGGER", "").strip().lower() in {"1", "true", "on", "yes"}:
        return {"present": False, "patched": [], "skipped": "SONIC_CONSOLE_LOGGER=1"}

    report: dict[str, Any] = {"present": False, "patched": []}

    # 1) Env kill switch for any code that reads it at runtime
    os.environ.setdefault("SONIC_CONSOLE_LOGGER", "0")

    try:
        from backend.core.monitor_core.console_logger import ConsoleLogger as CL  # type: ignore
        report["present"] = True
    except Exception:
        try:
            from backend.utils.console_logger import ConsoleLogger as CL  # type: ignore
            report["present"] = True
        except Exception:
            try:
                from console_logger import ConsoleLogger as CL  # type: ignore
                report["present"] = True
            except Exception:
                return report

    # 2) Runtime flag off
    try:
        CL.logging_enabled = False
        report["patched"].append("logging_enabled=False")
    except Exception:
        pass

    # 3) Force the activity check to always return False
    try:
        CL._active = classmethod(lambda *_a, **_k: False)  # type: ignore
        report["patched"].append("_active->False")
    except Exception:
        pass

    # 4) Monkey-patch all public writers to no-ops (belt & suspenders)
    def _noop(*_a: Any, **_k: Any) -> None:  # pragma: no cover
        return None

    for name in (
        "debug",
        "info",
        "success",
        "warning",
        "error",
        "critical",
        "exception",
        "banner",
        "start_timer",
        "end_timer",
        "init_status",
        "hijack_logger",
        "add_sink",
        "set_level",
        "print_dashboard_link",
        "route",
    ):
        if hasattr(CL, name):
            try:
                setattr(CL, name, classmethod(_noop))  # type: ignore
                report["patched"].append(f"{name}=noop")
            except Exception:
                pass

    return report


def emit_dashboard_link(host: str = "127.0.0.1", port: int = 5001, route: str = "/dashboard") -> None:
    """Emit the Sonic Dashboard URL via the new reporter (stdout print; downstream can wrap this)."""

    url = f"http://{host}:{port}{route}"
    print(f"🌐 Sonic Dashboard: {url}")


def emit_sources_line(sources: dict, label: str) -> None:
    if not sources:
        return
    blocks = []

    pr = sources.get("profit") or {}
    if pr:
        blocks.append("profit:{" + ",".join([
            f"pos={pr.get('pos','–') if pr.get('pos') not in (None,'') else '–'}",
            f"pf={pr.get('pf','–') if pr.get('pf') not in (None,'') else '–'}",
        ]) + "}")

    liq = sources.get("liquid") or {}
    if liq:
        blocks.append("liquid:{" + ",".join([
            f"btc={liq.get('btc','–') if liq.get('btc') not in (None,'') else '–'}",
            f"eth={liq.get('eth','–') if liq.get('eth') not in (None,'') else '–'}",
            f"sol={liq.get('sol','–') if liq.get('sol') not in (None,'') else '–'}",
        ]) + "}")

    if not blocks:
        return
    label_suffix = f" ← {label}" if label else ""
    line = "   🧭 Sources  : " + " ".join(blocks) + label_suffix
    print(line, flush=True)

# ---- One-time boot status line (for your vibe) --------------------------------

def emit_boot_status(muted: list[str], group_label: str = "", groups: list[str] | None = None) -> None:
    """Print muted modules once at startup (no Groups dump)."""
    m = ", ".join(muted) if muted else "–"
    print(f"🔒 Muted Modules:      {m}")
