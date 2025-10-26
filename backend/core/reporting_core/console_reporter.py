from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ───────────────────────── logger utils ─────────────────────────

_LOG = logging.getLogger("ConsoleReporter")
def _i(s: str, source: str | None = None) -> None:
    try:
        if source:
            logging.getLogger(source).info(s)
        else:
            _LOG.info(s)
    except Exception:
        pass

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

# ─────────────────────────────────────────────────────────────────────────────
# Thresholds panel (Option 3A rendered in console)
# ─────────────────────────────────────────────────────────────────────────────
def _num(v, default=None):
    try:
        if v is None:
            return default
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip().replace("%", "").replace(",", "")
        return float(s)
    except Exception:
        return default


def _fmt_pct(v: Optional[float]) -> str:
    return "—" if v is None else (f"{v:.2f}%" if (v < 1) else f"{v:.1f}%")


def _fmt_usd(v: Optional[float]) -> str:
    if v is None:
        return "—"
    try:
        return f"${v:,.2f}".rstrip("0").rstrip(".")
    except Exception:
        return f"${v}"


def _bar(util: Optional[float], width: int = 10) -> Tuple[str, str]:
    """Return (bar, label) where util is 0..1 (None => n/a)."""
    if util is None or util < 0 or not (util == util):  # NaN guard
        return "░" * width, "n/a"
    util = max(0.0, util)
    fill = min(width, int(round(util * width)))
    return "█" * fill + "░" * (width - fill), f"{int(round(util * 100))}%"


def _nearest_liq_from_db(dl) -> Dict[str, Optional[float]]:
    """
    Return minimum absolute liquidation distance per asset from positions.
    We keep this intentionally lenient: if the table/column isn’t there, we return {}.
    """
    try:
        cur = dl.db.get_cursor()
        if not cur:
            return {}
        cur.execute(
            """
            SELECT asset_type, MIN(ABS(liquidation_distance)) AS min_dist
              FROM positions
             WHERE status='ACTIVE'
            GROUP BY asset_type
            """
        )
        rows = cur.fetchall() or []
        out = {}
        for r in rows:
            # tolerate both mapping and tuple rows
            asset = (r["asset_type"] if "asset_type" in r.keys() else r[0]) if hasattr(r, "keys") else r[0]
            val   = (r["min_dist"]   if "min_dist"   in getattr(r, "keys", lambda: [])() else r[1])
            out[str(asset).upper()] = _num(val, None)
        return out
    except Exception:
        return {}


def _profit_actuals_from_db(dl) -> Tuple[float, float]:
    """
    Single = max positive pnl_after_fees_usd; Portfolio = sum of positives.
    This mirrors how your profit thresholds are compared (USD). :contentReference[oaicite:2]{index=2}
    """
    try:
        cur = dl.db.get_cursor()
        if not cur:
            return (0.0, 0.0)
        cur.execute("SELECT pnl_after_fees_usd FROM positions WHERE status='ACTIVE'")
        vals = []
        for r in cur.fetchall() or []:
            v = r["pnl_after_fees_usd"] if hasattr(r, "keys") and "pnl_after_fees_usd" in r.keys() else r[0]
            vals.append(_num(v, 0.0))
        positives = [v for v in vals if (isinstance(v, (int, float)) and v > 0)]
        single = max(positives) if positives else 0.0
        portfolio = sum(positives) if positives else 0.0
        return (single, portfolio)
    except Exception:
        return (0.0, 0.0)


def _resolve_liq_thresholds(liq_cfg: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """
    Accepts system var payload for 'liquid_monitor' and returns per-asset thresholds.
    Keys honored:
      - thresholds: {"BTC":..., "ETH":..., "SOL":...}
      - threshold_percent: number (global fallback)
    """
    thr_map = {}
    per = liq_cfg.get("thresholds") or {}
    glob = _num(liq_cfg.get("threshold_percent"))
    for sym in ("BTC", "ETH", "SOL"):
        thr_map[sym] = _num(per.get(sym), glob)
    return thr_map


def _resolve_profit_thresholds(prof_cfg: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """
    Accepts system var payload for 'profit_monitor' and returns (single, portfolio) USD thresholds.
    Keys honored: position_profit_usd, portfolio_profit_usd. :contentReference[oaicite:3]{index=3}
    """
    return (_num(prof_cfg.get("position_profit_usd")), _num(prof_cfg.get("portfolio_profit_usd")))


def emit_thresholds_panel(dl, csum: Dict[str, Any], ts_label: Optional[str] = None) -> None:
    """
    Print an icon-forward thresholds vs actuals panel (Option 3A) into the console.
    Controlled by SONIC_SHOW_THRESHOLDS (default on).
    """
    if os.getenv("SONIC_SHOW_THRESHOLDS", "1") == "0":
        return
    logger = logging.getLogger("SonicMonitor")
    _info = logger.info

    # Load config (system vars)
    try:
        sysvars = getattr(dl, "system", None)
    except Exception:
        sysvars = None
    liq_cfg  = (sysvars.get_var("liquid_monitor") if sysvars else {}) or {}
    prof_cfg = (sysvars.get_var("profit_monitor") if sysvars else {}) or {}

    liq_thr = _resolve_liq_thresholds(liq_cfg)
    prof_single_thr, prof_port_thr = _resolve_profit_thresholds(prof_cfg)

    nearest = _nearest_liq_from_db(dl)
    single_act, port_act = _profit_actuals_from_db(dl)

    # Header
    hdr = "🧭  Monitor Thresholds"
    if ts_label:
        hdr += f" — last cycle {ts_label}"
    _info(hdr)
    print(hdr, flush=True)

    def _row_liq(sym: str):
        actual = nearest.get(sym)
        thr    = liq_thr.get(sym)
        util   = (actual / thr) if (actual is not None and thr and thr > 0) else None
        bar, lab = _bar(util)
        name = "₿" if sym == "BTC" else ("Ξ" if sym == "ETH" else "◎")
        line = (
            f"{name} {sym} • 💧 Liquid".ljust(22)
            + f" {_fmt_pct(actual):>8} / {_fmt_pct(thr):<8}  {bar} {lab:>4}   🗄 DB"
        )
        _info(line)
        print(line, flush=True)

    for sym in ("BTC", "ETH", "SOL"):
        if (nearest.get(sym) is not None) or (liq_thr.get(sym) is not None):
            _row_liq(sym)

    def _row_profit(label: str, actual: Optional[float], thr: Optional[float]):
        util = (actual / thr) if (actual is not None and thr and thr > 0) else None
        bar, lab = _bar(util)
        line = (
            f"{label}".ljust(22)
            + f" {_fmt_usd(actual):>10} / {_fmt_usd(thr):<10}  {bar} {lab:>4}   🗄 DB"
        )
        _info(line)
        print(line, flush=True)

    _row_profit("👤 Single • 💹 Profit",   single_act, prof_single_thr)
    _row_profit("🧺 Portfolio • 💹 Profit", port_act,   prof_port_thr)

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
    "emit_thresholds_panel",
]
