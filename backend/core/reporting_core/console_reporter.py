from __future__ import annotations

import logging
import os
from typing import Iterable

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
    return env_list or DEFAULT_BLOCKLIST

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

# ---- One-time boot status line (for your vibe) --------------------------------

def emit_boot_status(muted: list[str], group_label: str = "cyclone_core", groups: list[str] | None = None) -> None:
    """Reproduce the nice 'Muted Modules' / 'Groups' lines once at startup."""
    m = ", ".join(muted) if muted else "–"
    print(f"🔒 Muted Modules:      {m}")
    if groups:
        joined = ", ".join(groups)
        print(f"    🧠 Groups:\n        {group_label} ➜ {joined}")
