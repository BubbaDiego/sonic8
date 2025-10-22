from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

_LOG = logging.getLogger("ConsoleReporter")
def _i(s: str) -> None:
    try:
        _LOG.info(s)
    except Exception:
        pass

# ---------- console noise control ----------
class StrictWhitelistFilter(logging.Filter):
    def __init__(self, *names: str) -> None:
        super().__init__()
        self._names = set(names or ("SonicMonitor", "ConsoleReporter"))

    def filter(self, rec: logging.LogRecord) -> bool:  # type: ignore[override]
        try:
            if rec.levelno >= logging.WARNING:
                return True
            return rec.name in self._names
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


def silence_legacy_console_loggers(
    names: list[str] | None = None, *, level: int = logging.ERROR
) -> None:
    return neuter_legacy_console_logger(names, level=level)


# ---------- tiny style helpers ----------
def _c(s: str, code: int) -> str:
    if sys.stdout.isatty():
        return f"\x1b[{code}m{s}\x1b[0m"
    return s


def _fmt_prices_line(
    top3: Iterable[Tuple[str, float]] | None,
    ages: Dict[str, int] | None = None,
    *,
    enable_color: bool = False,
) -> str:
    if not top3:
        return "–"
    ages = ages or {}
    parts = []
    for sym, val in top3:
        age = ages.get(sym.upper(), 0)
        badge = "" if not age else f"·{age}c"
        parts.append(f"{sym} ${val:,.2f}{badge}")
    return "  ".join(parts)


def _fmt_monitors(mon: Dict[str, Any] | None) -> str:
    if not mon:
        return "–"
    en = mon.get("enabled") or mon.get("monitors_enabled") or {}
    parts = []
    for k in ("liquid", "profit", "market", "price"):
        if k in en:
            parts.append(f"{k} ({'🛠️' if en.get(k) else '✖'})")
    return "  ".join(parts) if parts else "–"


# ---------- alerts detail formatters ----------
def _fmt_liquid(rows: List[Dict[str, Any]] | None) -> List[str]:
    if not rows:
        return ["✓"]
    out = []
    for r in rows:
        a = str((r or {}).get("asset") or (r or {}).get("symbol") or "—")
        d = r.get("distance")
        t = r.get("threshold")
        if d is None or t is None:
            continue
        sev = str(r.get("severity") or "").lower()
        tag = "breach" if sev == "breach" else ("near" if sev == "near" else "ok")
        out.append(f"{a} {float(d):.1f}% / thr {float(t):.1f}%  ({tag})")
    return out or ["✓"]


def _fmt_profit(rows: List[Dict[str, Any]] | None) -> List[str]:
    if not rows:
        return ["✓"]
    out = []
    for r in rows:
        metric = str(r.get("metric") or "pf").lower()
        label = "portfolio" if metric in ("pf", "portfolio") else "position"
        v = r.get("value")
        t = r.get("threshold")
        if v is None or t is None:
            continue
        sev = str(r.get("severity") or "").lower()
        tag = "breach" if sev == "breach" else ("near" if sev == "near" else "ok")
        out.append(f"{label} {float(v):.1f} / thr {float(t):.1f}  ({tag})")
    return out or ["✓"]


def _emit_alerts_block(csum: Dict[str, Any]) -> None:
    # aligned blue header (same column as Hedges/Notifications)
    print(_c("   🔔 Alerts   :", 94))
    detail = (
        (csum.get("alerts") or {}).get("detail") or {}
        if isinstance(csum.get("alerts"), dict)
        else {}
    )
    for key, title, fn in (
        ("profit", "Profit", _fmt_profit),
        ("liquid", "Liquid", _fmt_liquid),
        ("market", "Market", lambda _:["✓"]),
        ("price", "Price", lambda _:["✓"]),
    ):
        rows = detail.get(key) if isinstance(detail, dict) else None
        lines = fn(rows)
        print(f"      {title:<7}: ", end="")
        if lines == ["✓"]:
            print("✓")
        else:
            print(lines[0])
            for more in lines[1:]:
                print(f"                 {more}")


# ---------- compact cycle renderer ----------
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

    print(
        "   💰 Prices   : "
        + _fmt_prices_line(csum.get("prices_top3", []), csum.get("price_ages", {}), enable_color)
    )
    print(f"   📊 Positions: {positions.get('sync_line', '–')}")
    print(f"   🛡 Hedges   : {'🦔' if int(hedges.get('groups', 0) or 0) > 0 else '–'}")

    _emit_alerts_block(csum)

    notif = csum.get("notifications_brief", "NONE (no_breach)")
    print(f"   📨 Notifications : {notif}")
    print(f"   📡 Monitors : {_fmt_monitors(monitors)}")

    tail = f"✅ cycle #{loop_counter} done • {total_elapsed:.2f}s  (sleep {sleep_time:.1f}s)"
    _i(tail)
    print(tail, flush=True)


# ---------- optional sources & jsonl ----------
def emit_sources_line(sources: Dict[str, Any], label: str = "") -> None:
    if not sources:
        return
    blocks = []
    prof = sources.get("profit") or {}
    if prof:
        blocks.append(
            "profit:{pos="
            + str(prof.get("pos", "–"))
            + ",pf="
            + str(prof.get("pf", "–"))
            + "}"
        )
    liq = sources.get("liquid") or {}
    if liq:
        blocks.append(
            "liquid:{btc="
            + str(liq.get("btc", "–"))
            + ",eth="
            + str(liq.get("eth", "–"))
            + ",sol="
            + str(liq.get("sol", "–"))
            + "}"
        )
    if not blocks:
        return
    line = "   🧭 Sources  : " + " ".join(blocks) + (f" ← {label}" if label else "")
    _i(line)
    print(line, flush=True)


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
        p = Path("logs")
        p.mkdir(exist_ok=True)
        with (p / "sonic_summary.jsonl").open("a", encoding="utf-8") as f:
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
