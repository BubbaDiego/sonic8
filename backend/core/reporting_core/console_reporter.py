from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

# ───────────────────────── logger utils ─────────────────────────

_LOG = logging.getLogger("ConsoleReporter")
def _i(s: str) -> None:
    try: _LOG.info(s)
    except Exception: pass

class StrictWhitelistFilter(logging.Filter):
    def __init__(self, *names: str) -> None:
        super().__init__()
        self._names = set(names or ("SonicMonitor", "ConsoleReporter"))
    def filter(self, rec: logging.LogRecord) -> bool:  # type: ignore[override]
        try:
            if rec.levelno >= logging.WARNING: return True
            return rec.name in self._names
        except Exception:
            return True

def install_strict_console_filter() -> None:
    try:
        root = logging.getLogger()
        for h in root.handlers:
            if isinstance(h, logging.StreamHandler):
                h.addFilter(StrictWhitelistFilter())
    except Exception: pass

def neuter_legacy_console_logger(
    names: List[str] | None = None, *, level: int = logging.ERROR
) -> None:
    """Mute chatty loggers on console; keep WARNING/ERROR."""
    try:
        names = names or [
            "werkzeug", "uvicorn.access", "asyncio",
            "fuzzy_wuzzy", "ConsoleLogger", "console_logger", "LoggerControl",
        ]
        for n in names:
            lg = logging.getLogger(n); lg.setLevel(level); lg.propagate = False
            if not lg.handlers:
                lg.addHandler(logging.NullHandler())
    except Exception: pass

# Back-compat alias some builds import from sonic_monitor.py
def silence_legacy_console_loggers(
    names: list[str] | None = None, *, level: int = logging.ERROR
) -> None:
    return neuter_legacy_console_logger(names, level=level)

# ───────────────────────── style helpers ───────────────────────

def _c(s: str, code: int) -> str:
    """ANSI color if TTY."""
    if sys.stdout.isatty():
        return f"\x1b[{code}m{s}\x1b[0m"
    return s

def _fmt_prices_line(
    top3: Iterable[Tuple[str, float]] | None,
    ages: Dict[str, int] | None = None,
    *,
    enable_color: bool = False,
) -> str:
    if not top3: return "–"
    ages = ages or {}
    parts: List[str] = []
    for sym, val in top3:
        age = ages.get(sym.upper(), 0)
        badge = "" if not age else f"·{age}c"
        parts.append(f"{sym} ${val:,.2f}{badge}")
    return "  ".join(parts)

def _fmt_monitors(mon: Dict[str, Any] | None) -> str:
    if not mon: return "–"
    en = mon.get("enabled") or mon.get("monitors_enabled") or {}
    order = ("liquid", "profit", "market", "price")
    parts: List[str] = []
    for k in order:
        if k in en:
            parts.append(f"{k} ({'🛠️' if en.get(k) else '✖'})")
    return "  ".join(parts) if parts else "–"

# ───────────────────── Alerts detail formatters ─────────────────

def _fmt_liquid(rows: List[Dict[str, Any]] | None) -> List[str]:
    if not rows: return ["✓"]
    out: List[str] = []
    for r in rows:
        if not isinstance(r, dict): continue
        a = str(r.get("asset") or r.get("symbol") or "—")
        d = r.get("distance"); t = r.get("threshold")
        if d is None or t is None: continue
        sev = str(r.get("severity") or "").lower()
        tag = "breach" if sev == "breach" else ("near" if sev == "near" else "ok")
        out.append(f"{a} {float(d):.1f}% / thr {float(t):.1f}%  ({tag})")
    return out or ["✓"]

def _fmt_profit(rows: List[Dict[str, Any]] | None) -> List[str]:
    if not rows: return ["✓"]
    out: List[str] = []
    for r in rows:
        if not isinstance(r, dict): continue
        metric = str(r.get("metric") or "pf").lower()
        label  = "portfolio" if metric in ("pf", "portfolio") else "position"
        v = r.get("value"); t = r.get("threshold")
        if v is None or t is None: continue
        sev = str(r.get("severity") or "").lower()
        tag = "breach" if sev == "breach" else ("near" if sev == "near" else "ok")
        out.append(f"{label} {float(v):.1f} / thr {float(t):.1f}  ({tag})")
    return out or ["✓"]

def _ensure_detail_and_sources(csum: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tolerant enrichment: if the cycle did NOT include alerts.detail or sources,
    synthesize minimal structures so the console can render multi-line Alerts.
    """
    alerts = csum.setdefault("alerts", {})
    detail = alerts.get("detail")
    # quick 'sources' snapshot if missing (best-effort)
    if not isinstance(csum.get("sources"), dict):
        src: Dict[str, Any] = {}
        # profit pos/pf if present anywhere in summary
        pos = csum.get("profit", {}).get("settings", {}).get("pos")
        pf  = csum.get("profit", {}).get("settings", {}).get("pf")
        src["profit"] = {"pos": pos, "pf": pf}
        # liquid per-asset
        thr = (csum.get("liquid", {}) or {}).get("thresholds") or {}
        src["liquid"] = {
            "btc": thr.get("BTC") if isinstance(thr, dict) else None,
            "eth": thr.get("ETH") if isinstance(thr, dict) else None,
            "sol": thr.get("SOL") if isinstance(thr, dict) else None,
        }
        csum["sources"] = src

    if isinstance(detail, dict):
        return csum  # already provided by monitors

    # synthesize very small detail from whatever metrics exist
    out: Dict[str, List[Dict[str, Any]]] = {}
    prof_cur = (csum.get("profit") or {}).get("metrics") or {}
    pf_val  = prof_cur.get("pf_current")
    pos_val = prof_cur.get("pos_current")
    pf_thr  = csum.get("sources", {}).get("profit", {}).get("pf")
    pos_thr = csum.get("sources", {}).get("profit", {}).get("pos")
    rows: List[Dict[str, Any]] = []
    try:
        if pf_val is not None and pf_thr is not None:
            rows.append({"metric": "pf", "value": float(pf_val), "threshold": float(pf_thr),
                         "severity": "breach" if float(pf_val) >= float(pf_thr) else "ok"})
        if pos_val is not None and pos_thr is not None:
            rows.append({"metric": "pos", "value": float(pos_val), "threshold": float(pos_thr),
                         "severity": "breach" if float(pos_val) >= float(pos_thr) else "ok"})
    except Exception:
        rows = rows  # keep whatever we could parse
    if rows: out["profit"] = rows

    liq_assets = (csum.get("liquid") or {}).get("assets") or {}
    liq_thr    = csum.get("sources", {}).get("liquid", {}) or {}
    lrows: List[Dict[str, Any]] = []
    for a, cur in (liq_assets.items() if isinstance(liq_assets, dict) else []):
        dist = (cur or {}).get("distance")
        thr  = liq_thr.get(a.upper())
        try:
            if dist is None or thr is None: continue
            d = float(str(dist).replace("%",""))
            t = float(str(thr).replace("%",""))
            sev = "breach" if d <= t else "ok"
            lrows.append({"asset": a.upper(), "distance": d, "threshold": t, "severity": sev})
        except Exception:
            continue
    if lrows: out["liquid"] = lrows

    alerts["detail"] = out
    return csum

def _emit_alerts_block(csum: Dict[str, Any]) -> None:
    """Blue header aligned with top-level rows; then one line per monitor."""
    _ensure_detail_and_sources(csum)
    detail = (csum.get("alerts") or {}).get("detail") or {}

    print(_c("   🔔 Alerts   :", 94))  # bright blue, aligned with Notifications
    for key, title, fn in (
        ("profit", "Profit", _fmt_profit),
        ("liquid", "Liquid", _fmt_liquid),
        ("market", "Market", lambda _:[ "✓"]),
        ("price",  "Price",  lambda _:[ "✓"]),
    ):
        rows  = detail.get(key) if isinstance(detail, dict) else None
        lines = fn(rows)
        print(f"      {title:<7}: ", end="")
        if lines == ["✓"]:
            print("✓")
        else:
            print(lines[0])
            for more in lines[1:]:
                print(f"                 {more}")

# ───────────────────────── main compact renderer ─────────────────

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
    prices    = csum.get("prices", {}) or {}
    positions = csum.get("positions", {}) or {}
    hedges    = csum.get("hedges", {}) or {}
    monitors  = csum.get("monitors", {}) or {}

    print("   💰 Prices   : " + _fmt_prices_line(csum.get("prices_top3", []), csum.get("price_ages", {}), enable_color))
    print(f"   📊 Positions: {positions.get('sync_line', '–')}")
    print(f"   🛡 Hedges   : {'🦔' if int(hedges.get('groups', 0) or 0) > 0 else '–'}")

    _emit_alerts_block(csum)

    notif_line = csum.get("notifications_brief", "NONE (no_breach)")
    print(f"   📨 Notifications : {notif_line}")

    print(f"   📡 Monitors : {_fmt_monitors(monitors)}")

    tail = f"✅ cycle #{loop_counter} done • {total_elapsed:.2f}s  (sleep {sleep_time:.1f}s)"
    _i(tail); print(tail, flush=True)

# ───────────────────── optional sources/jsonl ───────────────────

def emit_sources_line(sources: Dict[str, Any], label: str = "") -> None:
    if not sources: return
    blocks: List[str] = []
    prof = sources.get("profit") or {}
    liq  = sources.get("liquid") or {}
    blocks.append("profit:{pos="+str(prof.get("pos","–"))+",pf="+str(prof.get("pf","–"))+"}")
    blocks.append("liquid:{btc="+str(liq.get("btc","–"))+",eth="+str(liq.get("eth","–"))+",sol="+str(liq.get("sol","–"))+"}")
    line = "   🧭 Sources  : " + " ".join(blocks) + (f" ← {label}" if label else "")
    _i(line); print(line, flush=True)

def emit_json_summary(csum: Dict[str, Any], cyc_ms: int, loop_counter: int, total_elapsed: float, sleep_time: float) -> None:
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
        p = Path("logs"); p.mkdir(exist_ok=True)
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
