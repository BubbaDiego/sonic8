import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple, Optional

from .console_reporter import emit_compact_cycle as _emit_compact_cycle7

# -------------------------------------------------------------------
# Logging helpers
# -------------------------------------------------------------------
_LOG = logging.getLogger("ConsoleReporter")

def _i(line: str) -> None:
    try:
        _LOG.info(line)
    except Exception:
        pass

class StrictWhitelistFilter(logging.Filter):
    """Allow only whitelisted logger names at INFO; always allow WARNING+."""
    def __init__(self, *names: str) -> None:
        super().__init__()
        self._names = set(names or ("SonicMonitor", "ConsoleReporter"))

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        try:
            if record.levelno >= logging.WARNING:
                return True
            return record.name in self._names
        except Exception:
            return True

def install_strict_console_filter() -> None:
    """Install a strict filter on stream handlers (keeps compact mode tidy)."""
    try:
        root = logging.getLogger()
        for h in root.handlers:
            if isinstance(h, logging.StreamHandler):
                h.addFilter(StrictWhitelistFilter())
    except Exception:
        pass

def neuter_legacy_console_logger(
    names: Optional[List[str]] = None, *, level: int = logging.ERROR
) -> None:
    """
    Mute chatty loggers on console; keep WARNING/ERROR.
    Back-compat shim expected by the monitor runner.
    """
    try:
        names = names or [
            "werkzeug",
            "uvicorn.access",
            "asyncio",
            "fuzzy_wuzzy",
            "ConsoleLogger",
            "console_logger",
            "LoggerControl",
        ]
        for n in names:
            lg = logging.getLogger(n)
            lg.setLevel(level)
            lg.propagate = False
            if not lg.handlers:
                lg.addHandler(logging.NullHandler())
    except Exception:
        pass

# Back-compat alias some builds import
def silence_legacy_console_loggers(
    names: Optional[List[str]] = None, *, level: int = logging.ERROR
) -> None:
    return neuter_legacy_console_logger(names, level=level)

# -------------------------------------------------------------------
# Small formatting helpers
# -------------------------------------------------------------------
def _c(s: str, code: int) -> str:
    """Colorize with ANSI if stdout is a TTY; else return s."""
    if sys.stdout.isatty():
        return f"\x1b[{code}m{s}\x1b[0m"
    return s

def _fmt_prices_line(
    top3: Optional[Iterable[Tuple[str, float]]],
    ages: Optional[Dict[str, int]] = None,
    # NOTE: accept enable_color as a *positional* third arg to match legacy callers
    enable_color: bool = False,
) -> str:
    """
    Keep the third positional parameter to accept legacy calls like:
        _fmt_prices_line(top3, ages, enable_color)
    We currently ignore enable_color here; colorization is handled by _c().
    """
    if not top3:
        return "–"
    ages = ages or {}
    parts: List[str] = []
    for sym, val in top3:
        age = ages.get(str(sym).upper(), 0)
        badge = "" if not age else f"·{age}c"
        parts.append(f"{sym} ${val:,.2f}{badge}")
    return "  ".join(parts)

def _fmt_monitors(monitors: Optional[Dict[str, Any]]) -> str:
    if not monitors:
        return "–"
    en = monitors.get("enabled") or monitors.get("monitors_enabled") or {}
    pieces: List[str] = []
    for key in ("liquid", "profit", "market", "price"):
        if key in en:
            pieces.append(f"{key} ({'🛠️' if en.get(key) else '✖'})")
    return "  ".join(pieces) if pieces else "–"

# -------------------------------------------------------------------
# Alerts detail formatting (per-monitor)
# -------------------------------------------------------------------
def _fmt_liquid_detail(rows: Optional[List[Dict[str, Any]]]) -> List[str]:
    if not rows:
        return ["✓"]
    out: List[str] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        asset = str(r.get("asset") or r.get("symbol") or "—")
        dist = r.get("distance"); thr = r.get("threshold")
        if dist is None or thr is None:
            continue
        try:
            d = float(str(dist).replace("%", ""))
            t = float(str(thr).replace("%", ""))
        except Exception:
            continue
        sev = str(r.get("severity") or "").lower()
        tag = "breach" if sev == "breach" else ("near" if sev == "near" else "ok")
        out.append(f"{asset} {d:.1f}% / thr {t:.1f}%  ({tag})")
    return out or ["✓"]

def _fmt_profit_detail(rows: Optional[List[Dict[str, Any]]]) -> List[str]:
    if not rows:
        return ["✓"]
    out: List[str] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        metric = str(r.get("metric") or "pf").lower()
        label  = "portfolio" if metric in ("pf", "portfolio") else "position"
        val = r.get("value"); thr = r.get("threshold")
        if val is None or thr is None:
            continue
        try:
            v = float(val); t = float(thr)
        except Exception:
            continue
        sev = str(r.get("severity") or "").lower()
        tag = "breach" if sev == "breach" else ("near" if sev == "near" else "ok")
        out.append(f"{label} {v:.1f} / thr {t:.1f}  ({tag})")
    return out or ["✓"]

def _emit_alerts_block(csum: Dict[str, Any]) -> None:
    """
    Print aligned blue '🔔 Alerts' header, then one indented line per monitor.
    Falls back to ✓ when no detail is available.
    """
    alerts = csum.get("alerts") or {}
    detail = alerts.get("detail") or {}

    # Aligned header (same column as Hedges / Notifications)
    print(_c("   🔔 Alerts   :", 94), flush=True)

    for mon_key, title, fmt in (
        ("profit", "Profit", _fmt_profit_detail),
        ("liquid", "Liquid", _fmt_liquid_detail),
        ("market", "Market", lambda _: ["✓"]),
        ("price",  "Price",  lambda _: ["✓"]),
    ):
        rows = detail.get(mon_key) if isinstance(detail, dict) else None
        lines = fmt(rows)
        print(f"      {title:<7}: ", end="")
        if lines == ["✓"]:
            print("✓", flush=True)
        else:
            print(lines[0], flush=True)
            for more in lines[1:]:
                print(f"                 {more}", flush=True)

# -------------------------------------------------------------------
# Compact cycle renderer (legacy shim -> new signature)
# -------------------------------------------------------------------
def emit_compact_cycle(
    summary: Dict[str, Any],
    cfg: Dict[str, Any],
    poll_interval_s: int,
    *,
    enable_color: bool = False,
    loop_counter: Optional[int] = None,
    total_elapsed: Optional[float] = None,
    sleep_time: Optional[float] = None,
    dl: Any | None = None,
) -> None:
    """
    Wrapper that keeps legacy 4-arg callers working by deriving
    timing fields expected by the newer 7-arg compact printer.
    """
    summary = summary or {}
    cfg = cfg or {}

    durations = summary.get("durations")
    if not isinstance(durations, dict):
        durations = {}

    elapsed_s = summary.get("elapsed_s") or 0.0
    try:
        elapsed_s = float(elapsed_s)
    except Exception:
        elapsed_s = 0.0

    cyc_ms = durations.get("cyclone_ms") or durations.get("cycle_ms")
    try:
        cyc_ms = int(cyc_ms)
    except Exception:
        cyc_ms = 0

    if cyc_ms <= 0 and elapsed_s:
        cyc_ms = max(1, int(round(elapsed_s * 1000.0)))
    if cyc_ms <= 0:
        cyc_ms = 1

    if loop_counter is not None:
        lc = loop_counter
    else:
        lc = (
            summary.get("cycle_num")
            or summary.get("loop_counter")
            or (summary.get("loop") or {}).get("n")
            or -1
        )
    try:
        lc = int(lc)
    except Exception:
        lc = -1

    if total_elapsed is not None:
        tot = total_elapsed
    else:
        tot = elapsed_s if elapsed_s else (cyc_ms / 1000.0)
    try:
        tot = float(tot)
    except Exception:
        tot = float(cyc_ms) / 1000.0

    try:
        poll_interval_f = float(poll_interval_s)
    except Exception:
        poll_interval_f = 0.0

    if poll_interval_f < 0:
        poll_interval_f = 0.0

    if sleep_time is not None:
        slp = sleep_time
    else:
        slp = max(0.0, poll_interval_f - float(tot or 0.0))
    try:
        slp = float(slp)
    except Exception:
        slp = 0.0

    try:
        interval_int = int(poll_interval_f)
    except Exception:
        interval_int = 0

    _emit_compact_cycle7(
        summary,
        cyc_ms,
        interval_int,
        int(lc),
        float(tot),
        float(slp),
        enable_color=enable_color,
    )

    # Back-compat: cfg is currently unused but retained for signature parity
    _ = cfg

# -------------------------------------------------------------------
# Optional “Sources” line (threshold provenance) and JSONL
# -------------------------------------------------------------------
def emit_sources_line(sources: Dict[str, Any], label: str = "") -> None:
    """Legacy no-op retained for back-compat with older monitor builds."""
    # (UX) Sources line removed
    return

def emit_json_summary(
    csum: Dict[str, Any],
    cyc_ms: int,
    loop_counter: int,
    total_elapsed: float,
    sleep_time: float,
) -> None:
    out = {
        "cycle": loop_counter,
        "durations_ms": {"cyclone": int(cyc_ms), "total": int(total_elapsed * 1000)},
        "sleep_s": round(sleep_time, 3),
        "prices": csum.get("prices", {}),
        "positions": csum.get("positions", {}),
        "hedges": csum.get("hedges", {}),
        "alerts": csum.get("alerts", {}),
        "monitors": csum.get("monitors", {}),
        "ts": int(time.time()),
    }
    try:
        logs = Path("logs")
        logs.mkdir(exist_ok=True)
        with (logs / "sonic_summary.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
    except Exception:
        pass

__all__ = [
    "StrictWhitelistFilter",
    "install_strict_console_filter",
    "neuter_legacy_console_logger",
    "silence_legacy_console_loggers",
    "emit_compact_cycle",
    "emit_sources_line",
    "emit_json_summary",
]
