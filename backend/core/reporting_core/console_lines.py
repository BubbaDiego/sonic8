import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple, Optional

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
# Compact cycle renderer (new signature)
# -------------------------------------------------------------------
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
    New reporter signature used by the console_lines shim (which adapts
    legacy callers to provide cyc_ms/loop_counter/total_elapsed/sleep_time).
    """
    prices = csum.get("prices") or {}
    positions = csum.get("positions") or {}
    hedges = csum.get("hedges") or {}
    monitors = csum.get("monitors") or {}

    # Top rows
    print("   💰 Prices   : " + _fmt_prices_line(
        csum.get("prices_top3", []),
        csum.get("price_ages", {}),
        enable_color  # accept positional 3rd arg, safe even if ignored
    ))
    print(f"   📊 Positions: {positions.get('sync_line', '–')}")
    # Keep Hedges aligned with Alerts/Notifications column
    print(f"   🛡 Hedges   : {'🦔' if int(hedges.get('groups', 0) or 0) > 0 else '–'}")

    # Multi-line Alerts
    _emit_alerts_block(csum)

    # Notifications (actual dispatch outcomes only)
    notif_line = csum.get("notifications_brief", "NONE (no_breach)")
    print(f"   📨 Notifications : {notif_line}")

    # Monitors summary
    print(f"   📡 Monitors : {_fmt_monitors(monitors)}")

    # Tail
    tail = f"✅ cycle #{loop_counter} done • {total_elapsed:.2f}s  (sleep {sleep_time:.1f}s)"
    _i(tail)
    print(tail, flush=True)

# -------------------------------------------------------------------
# Optional “Sources” line (threshold provenance) and JSONL
# -------------------------------------------------------------------
def emit_sources_line(sources: Dict[str, Any], label: str = "") -> None:
    """Legacy no-op retained for back-compat with older monitor builds."""
    # (UX) Sources line removed — Sync Data + Evaluations now show provenance
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
