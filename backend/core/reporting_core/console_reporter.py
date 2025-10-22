from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


# -----------------------------------------------------------------------------
# Logging helpers
# -----------------------------------------------------------------------------
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
    try:
        root = logging.getLogger()
        for h in root.handlers:
            if isinstance(h, logging.StreamHandler):
                h.addFilter(StrictWhitelistFilter())
    except Exception:
        pass


def neuter_legacy_console_logger(
    names: List[str] | None = None, *, level: int = logging.ERROR
) -> None:
    """Mute chatty loggers on console; keep WARNING/ERROR."""
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


# Back-compat alias used by sonic_monitor.py
def silence_legacy_console_loggers(
    names: list[str] | None = None, *, level: int = logging.ERROR
) -> None:
    return neuter_legacy_console_logger(names, level=level)


def install_legacy_capture_file(path: str = "logs/sonic_console.log") -> None:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(p, encoding="utf-8")
        fh.setLevel(logging.INFO)
        logging.getLogger().addHandler(fh)
    except Exception:
        pass


# -----------------------------------------------------------------------------
# Banner (minimal)
# -----------------------------------------------------------------------------
def _mask(s: str, left: int = 3, right: int = 2) -> str:
    if not s or s == "–":
        return "–"
    if len(s) <= left + right:
        return s[0] + "…" + s[-1]
    return s[:left] + "…" + s[-right:]


def emit_config_banner(dl: Any, interval_probe: int | None) -> None:
    try:
        db_path = getattr(getattr(dl, "db", None), "db_path", "unknown")
    except Exception:
        db_path = "unknown"
    dotenv_path = ""
    try:
        from dotenv import find_dotenv  # type: ignore
        dotenv_path = find_dotenv(usecwd=True) or ""
    except Exception:
        pass
    rpc = os.getenv("PERP_RPC_URL") or os.getenv("ANCHOR_PROVIDER_URL") or os.getenv("RPC") or ""
    helius_key = os.getenv("HELIUS_API_KEY") or "–"

    lines = [
        "══════════════════════════════════════════════════════════════",
        "   🦔 Sonic Monitor Configuration",
        "══════════════════════════════════════════════════════════════",
        f"📦 Database : {db_path}",
        f"🗒  .env     : {dotenv_path or 'not found'}",
        f"⏱  Interval : {interval_probe}s" if interval_probe is not None else None,
        f"🌐 RPC      : {rpc if rpc else '–'}",
        f"🔐 Helius   : {_mask(helius_key)}" if helius_key and helius_key != "–" else None,
        "══════════════════════════════════════════════════════════════",
    ]
    for line in filter(None, lines):
        _i(line)
        print(line, flush=True)


# -----------------------------------------------------------------------------
# Pretty helpers
# -----------------------------------------------------------------------------
def _fmt_prices_line(
    top3: Iterable[Tuple[str, float]] | None,
    ages: Dict[str, int] | None = None,
    *,
    enable_color: bool = False,
) -> str:
    if not top3:
        return "–"
    out: List[str] = []
    ages = ages or {}
    for sym, val in top3:
        age = ages.get(sym.upper(), 0)
        badge = "" if age in (0, None) else f"·{age}c"
        out.append(f"{sym} ${val:,.2f}{badge}")
    return "  ".join(out)


def _fmt_monitors(monitors: Dict[str, Any] | None) -> str:
    if not monitors:
        return "–"
    en = monitors.get("enabled") or monitors.get("monitors_enabled") or {}
    ch = monitors.get("channels") or monitors.get("monitors_channels") or {}
    order = ("liquid", "profit", "market", "price")
    parts: List[str] = []
    for key in order:
        if key not in en:
            continue
        enabled = bool(en.get(key))
        core = "🛠️" if enabled else "✖"
        icons = " " + " ".join(ch.get(key, [])) if enabled and ch.get(key) else ""
        parts.append(f"{key} ({core}{icons})")
    return "  ".join(parts) if parts else "–"


# ---- color -------------------------------------------------------------------
def _c(s: str, code: int) -> str:
    """Colorize with ANSI if TTY; otherwise return string unchanged."""
    if sys.stdout.isatty():
        return f"\x1b[{code}m{s}\x1b[0m"
    return s


# ---- Alerts detail formatting ------------------------------------------------
def _fmt_liquid_detail(rows: List[Dict[str, Any]] | None) -> List[str]:
    if not rows:
        return ["✓"]
    out: List[str] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        asset = str(r.get("asset") or r.get("symbol") or "—")
        dist = r.get("distance")
        thr = r.get("threshold")
        sev = (str(r.get("severity") or "")).lower()
        if dist is None or thr is None:
            continue
        tag = "breach" if sev == "breach" else ("near" if sev == "near" else "ok")
        out.append(f"{asset} {float(dist):.1f}% / thr {float(thr):.1f}%  ({tag})")
    return out or ["✓"]


def _fmt_profit_detail(rows: List[Dict[str, Any]] | None) -> List[str]:
    if not rows:
        return ["✓"]
    out: List[str] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        metric = (str(r.get("metric") or "pf")).lower()  # 'pf' or 'pos'
        label = "portfolio" if metric in ("pf", "portfolio") else "position"
        val = r.get("value")
        thr = r.get("threshold")
        sev = (str(r.get("severity") or "")).lower()
        if val is None or thr is None:
            continue
        tag = "breach" if sev == "breach" else ("near" if sev == "near" else "ok")
        out.append(f"{label} {float(val):.1f} / thr {float(thr):.1f}  ({tag})")
    return out or ["✓"]


def _emit_alerts_block(csum: Dict[str, Any]) -> None:
    """Aligned blue '🔔 Alerts' header; then one line per monitor."""
    alerts = csum.get("alerts") or {}
    detail = alerts.get("detail") or {}
    # header aligned with Notifications (blue)
    print(_c("   🔔 Alerts   :", 94), flush=True)  # 94 = bright blue
    # one line per monitor
    for mon_key, title, fn in (
        ("profit", "Profit", _fmt_profit_detail),
        ("liquid", "Liquid", _fmt_liquid_detail),
        ("market", "Market", lambda _: ["✓"]),
        ("price", "Price", lambda _: ["✓"]),
    ):
        rows = detail.get(mon_key) if isinstance(detail, dict) else None
        lines = fn(rows)
        print(f"      {title:<7}: ", end="", flush=False)
        if lines == ["✓"]:
            print("✓", flush=True)
        else:
            print(lines[0], flush=True)
            for extra in lines[1:]:
                print(f"                 {extra}", flush=True)


# -----------------------------------------------------------------------------
# Compact cycle
# -----------------------------------------------------------------------------
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
    prices = csum.get("prices", {}) or {}
    positions = csum.get("positions", {}) or {}
    hedges = csum.get("hedges", {}) or {}
    monitors = csum.get("monitors", {}) or {}

    print("   💰 Prices   : " + _fmt_prices_line(csum.get("prices_top3", []), csum.get("price_ages", {}), enable_color))
    print(f"   📊 Positions: {positions.get('sync_line', '–')}")
    brief = csum.get("positions_brief", "–")
    print(f"   📄 Holdings : {brief}")
    print(f"   🛡 Hedges   : {'🦔' if int(hedges.get('groups', 0) or 0) > 0 else '–'}")

    # Alerts (multi-line, blue header)
    _emit_alerts_block(csum)

    # Notifications (dispatch outcomes only)
    notif_line = csum.get("notifications_brief", "NONE (no_breach)")
    print(f"   📨 Notifications : {notif_line}")

    # Monitors summary
    print(f"   📡 Monitors : {_fmt_monitors(monitors)}")

    tail = f"✅ cycle #{loop_counter} done • {total_elapsed:.2f}s  (sleep {sleep_time:.1f}s)"
    _i(tail)
    print(tail, flush=True)


# -----------------------------------------------------------------------------
# “Sources” line (optional)
# -----------------------------------------------------------------------------
def emit_sources_line(sources: Dict[str, Any], label: str = "") -> None:
    if not sources:
        return
    blocks: List[str] = []

    profit = sources.get("profit") or {}
    if profit:
        pos = profit.get("pos"); pf = profit.get("pf")
        blocks.append("profit:{" + ",".join([f"pos={pos if pos not in (None, '') else '–'}",
                                             f"pf={pf if pf not in (None, '') else '–'}"]) + "}")

    liquid = sources.get("liquid") or {}
    if liquid:
        btc = liquid.get("btc"); eth = liquid.get("eth"); sol = liquid.get("sol")
        blocks.append("liquid:{" + ",".join([f"btc={btc if btc not in (None, '') else '–'}",
                                             f"eth={eth if eth not in (None, '') else '–'}",
                                             f"sol={sol if sol not in (None, '') else '–'}"]) + "}")

    market = sources.get("market") or {}
    if market:
        parts = []
        for a in ("btc", "eth", "sol"):
            if a in market:
                val = market.get(a); parts.append(f"{a}=${val if val not in (None, '') else '–'}")
        if "rearm" in market: parts.append(f"rearm={market.get('rearm')}")
        if "sonic" in market: parts.append(f"sonic={market.get('sonic')}")
        if parts: blocks.append("market:{" + ",".join(parts) + "}")

    if not blocks:
        return

    label_suffix = f" ← {label}" if label else ""
    line = "   🧭 Sources  : " + " ".join(blocks) + label_suffix
    _i(line)
    print(line, flush=True)


# -----------------------------------------------------------------------------
# JSONL summary (unchanged)
# -----------------------------------------------------------------------------
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
        logs = Path("logs"); logs.mkdir(exist_ok=True)
        with (logs / "sonic_summary.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
    except Exception:
        pass


__all__ = [
    "StrictWhitelistFilter",
    "install_strict_console_filter",
    "install_legacy_capture_file",
    "neuter_legacy_console_logger",
    "silence_legacy_console_loggers",
    "emit_config_banner",
    "emit_compact_cycle",
    "emit_sources_line",
    "emit_json_summary",
]
