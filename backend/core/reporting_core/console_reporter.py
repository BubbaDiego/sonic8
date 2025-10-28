from __future__ import annotations

import importlib
import json as _json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    prices_top3,
    price_ages: dict | None = None,
    enable_color: bool = False,
) -> str:
    """
    Render a compact 'BTC 69.1k (0s) • ETH 4.5k (3s) • SOL 227.8 (—)' line.
    Accepts:
      - prices_top3: iterable of (asset, price) OR dicts with {'asset'|'symbol'|'market', 'price'|'current_price'}
      - price_ages: optional mapping {asset -> age_in_seconds or str}
      - enable_color: reserved; keep signature compatible with callers
    """

    def _abbr(n):
        try:
            v = float(n)
        except Exception:
            return str(n)
        abs_v = abs(v)
        if abs_v >= 1_000_000_000:
            return f"{v/1_000_000_000:.1f}B"
        if abs_v >= 1_000_000:
            return f"{v/1_000_000:.1f}M"
        if abs_v >= 1_000:
            return f"{v/1_000:.1f}k"
        return f"{v:.2f}".rstrip("0").rstrip(".")

    def _asset(x):
        # tuple/list -> first item; dict -> common keys
        if isinstance(x, (tuple, list)) and x:
            return str(x[0]).upper()
        if isinstance(x, dict):
            for k in ("asset", "symbol", "market"):
                if k in x and x[k]:
                    return str(x[k]).upper()
        return "?"

    def _price(x):
        if isinstance(x, (tuple, list)) and len(x) > 1:
            return x[1]
        if isinstance(x, dict):
            for k in ("price", "current_price", "last", "value"):
                if k in x and x[k] is not None:
                    return x[k]
        return None

    def _age_tag(sym: str) -> str:
        if not price_ages:
            return ""
        try:
            if hasattr(price_ages, "get"):
                age = price_ages.get(sym)
                if age is None:
                    age = price_ages.get(sym.upper())
            else:
                age = None
        except Exception:
            age = None
        if age is None or age == "":
            return "(—)"
        try:
            sec = float(age)
            if sec < 1:
                return "(0s)"
            if sec < 60:
                return f"({int(sec)}s)"
            m = int(sec // 60)
            return f"({m}m)"
        except Exception:
            return f"({age})"

    parts: List[str] = []
    for item in (prices_top3 or []):
        sym = _asset(item)
        price = _price(item)
        age = _age_tag(sym) if price_ages else ""
        pretty_price = _abbr(price) if price is not None else "—"
        parts.append(f"{sym} {pretty_price} {age}".rstrip())

    return " • ".join(parts) if parts else "–"

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


def _nearest_liq_from_db(dl, cycle_id: Optional[str] = None) -> Dict[str, Optional[float]]:
    """
    Return minimum absolute liquidation distance per asset.
    Prefer current cycle snapshot (sonic_positions) when cycle_id is provided;
    fall back to legacy positions table.
    We keep this intentionally lenient: if the table/column isn’t there, we return {}.
    """
    try:
        cur = dl.db.get_cursor()
        if not cur:
            return {}
        if cycle_id:
            cur.execute(
                """
                SELECT asset, MIN(ABS(liquidation_distance)) AS min_dist
                  FROM sonic_positions
                 WHERE cycle_id = ?
                GROUP BY asset
                """,
                (cycle_id,),
            )
        else:
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
            asset = (
                r["asset"] if hasattr(r, "keys") and "asset" in r.keys()
                else (r["asset_type"] if hasattr(r, "keys") and "asset_type" in r.keys() else r[0])
            ) or ""
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
    Keys honored: position_profit_usd, portfolio_profit_usd.
    """
    return (_num(prof_cfg.get("position_profit_usd")), _num(prof_cfg.get("portfolio_profit_usd")))


def _as_dict(v: Any) -> Dict[str, Any]:
    if isinstance(v, dict):
        return v
    if isinstance(v, str):
        try:
            parsed = _json.loads(v)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _fmt_num(v: Optional[float]) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.2f}".rstrip("0").rstrip(".")
    except Exception:
        return str(v)


def _src_label(v_src: str, t_src: str) -> str:
    v = "DB" if v_src == "db" else ("FILE" if v_src == "file" else "ENV" if v_src == "env" else v_src.upper())
    t = "DB" if t_src == "db" else ("FILE" if t_src == "file" else "ENV" if t_src == "env" else t_src.upper())
    return f"{v} / {t}"


def _classify_result(kind: str, actual: Optional[float], thr: Optional[float]) -> str:
    if actual is None or thr is None or thr <= 0:
        return "· no data"
    if kind == "liquid":
        if actual <= thr:
            return "🔴 HIT"
        if actual <= 1.2 * thr:
            return "🟡 NEAR"
        return "🟢 OK"
    if actual >= thr:
        return "🟢 HIT"
    if actual >= 0.8 * thr:
        return "🟡 NEAR"
    return "· not met"


# ---------- THRESHOLD TRACE (why we ended up with these numbers) ----------
def _scan_env_liquid() -> Dict[str, Optional[float]]:
    env: Dict[str, Optional[float]] = {
        "BTC": _num(os.getenv("LIQUID_THRESHOLD_BTC")),
        "ETH": _num(os.getenv("LIQUID_THRESHOLD_ETH")),
        "SOL": _num(os.getenv("LIQUID_THRESHOLD_SOL")),
    }
    glob = _num(os.getenv("LIQUID_THRESHOLD"))
    if glob is None:
        return env
    for sym in ("BTC", "ETH", "SOL"):
        if env.get(sym) is None:
            env[sym] = glob
    return env


def _resolve_liquid_sources(
    dl,
) -> tuple[Dict[str, Optional[float]], Dict[str, Optional[float]], Dict[str, Optional[float]], str]:
    """Return candidate liquidation thresholds from FILE, DB, ENV and winning label."""

    try:
        sysvars = getattr(dl, "system", None)
    except Exception:
        sysvars = None
    try:
        gconf = getattr(dl, "global_config", None)
    except Exception:
        gconf = None

    file_map: Dict[str, Optional[float]] = {"BTC": None, "ETH": None, "SOL": None}
    db_map: Dict[str, Optional[float]] = {"BTC": None, "ETH": None, "SOL": None}
    env_map: Dict[str, Optional[float]] = _scan_env_liquid()

    # FILE (json config)
    try:
        lm_file = _as_dict(gconf.get("liquid_monitor") if hasattr(gconf, "get") else {})
    except Exception:
        lm_file = {}
    if lm_file:
        thr_map = _as_dict(lm_file.get("thresholds") or {})
        glob = _num(lm_file.get("threshold_percent"))
        for sym in ("BTC", "ETH", "SOL"):
            file_map[sym] = _num(thr_map.get(sym), glob)

    # DB (system vars)
    try:
        lm_db_raw = sysvars.get_var("liquid_monitor") if sysvars else {}
    except Exception:
        lm_db_raw = {}
    lm_db = _as_dict(lm_db_raw)
    if lm_db:
        thr_map = _as_dict(lm_db.get("thresholds") or {})
        glob = _num(lm_db.get("threshold_percent"))
        for sym in ("BTC", "ETH", "SOL"):
            db_map[sym] = _num(thr_map.get(sym), glob)

    chosen_src = "file" if any(v is not None for v in file_map.values()) else (
        "db" if any(v is not None for v in db_map.values()) else (
            "env" if any(v is not None for v in env_map.values()) else "unknown"
        )
    )

    return file_map, db_map, env_map, chosen_src


def _resolve_profit_sources(dl) -> tuple[Dict[str, Optional[float]], str]:
    """Return profit thresholds (pos/pf) and the provenance label."""

    try:
        sysvars = getattr(dl, "system", None)
    except Exception:
        sysvars = None

    try:
        pm = _as_dict(sysvars.get_var("profit_monitor") if sysvars else {})
    except Exception:
        pm = {}

    pos_thr, pf_thr = _resolve_profit_thresholds(pm)
    src = "db" if any(v is not None for v in (pos_thr, pf_thr)) else "unknown"
    return {"pos": pos_thr, "pf": pf_thr}, src


def emit_thresholds_sync_step(dl) -> None:
    """Emit the always-on Sync Data thresholds snapshot."""

    logger = logging.getLogger("SonicMonitor")
    _info = logger.info

    t0 = time.perf_counter()

    file_map, db_map, env_map, _liq_src_overall = _resolve_liquid_sources(dl)
    prof_map, prof_src = _resolve_profit_sources(dl)

    used_liq: Dict[str, Optional[float]] = {}
    used_srcs: Dict[str, str] = {}
    for sym in ("BTC", "ETH", "SOL"):
        if file_map.get(sym) is not None:
            used_liq[sym] = file_map.get(sym)
            used_srcs[sym] = "FILE"
        elif db_map.get(sym) is not None:
            used_liq[sym] = db_map.get(sym)
            used_srcs[sym] = "DB"
        elif env_map.get(sym) is not None:
            used_liq[sym] = env_map.get(sym)
            used_srcs[sym] = "ENV"
        else:
            used_liq[sym] = None
            used_srcs[sym] = "—"

    dt = time.perf_counter() - t0
    header = f"  🧭 Read monitor thresholds  ✅ ({dt:.2f}s)"
    _info(header)
    print(header, flush=True)

    def _fmt_map(data: Dict[str, Optional[float]]) -> str:
        def _fmt(v: Optional[float]) -> str:
            if v is None:
                return "—"
            try:
                return f"{float(v):.2f}".rstrip("0").rstrip(".")
            except Exception:
                return str(v)

        return "BTC {btc} • ETH {eth} • SOL {sol}".format(
            btc=_fmt(data.get("BTC")),
            eth=_fmt(data.get("ETH")),
            sol=_fmt(data.get("SOL")),
        )

    src_tokens = [used_srcs.get(sym, "—") for sym in ("BTC", "ETH", "SOL")]
    if len(set(src_tokens)) == 1:
        src_label = src_tokens[0]
    else:
        src_label = "MIXED(" + ", ".join(
            f"{sym}={used_srcs.get(sym, '—')}" for sym in ("BTC", "ETH", "SOL")
        ) + ")"
    liquid_line = f"  💧 Liquid thresholds : {_fmt_map(used_liq)}   [{src_label}]"
    _info(liquid_line)
    print(liquid_line, flush=True)

    missing = [sym for sym in ("BTC", "ETH", "SOL") if file_map.get(sym) is None]
    if all(file_map.get(sym) is None for sym in ("BTC", "ETH", "SOL")):
        hint = (
            "  ↳ JSON config missing: liquid_monitor.thresholds not found; "
            "using DB/ENV fallbacks."
        )
        _info(hint)
        print(hint, flush=True)
    elif missing:
        hint = (
            "  ↳ JSON config partial: missing in FILE → "
            + ", ".join(missing)
            + ". Mixed with DB/ENV."
        )
        _info(hint)
        print(hint, flush=True)

    def _fmt_usd(value: Optional[float]) -> str:
        if value is None:
            return "—"
        try:
            return f"${float(value):.0f}"
        except Exception:
            return str(value)

    profit_line = (
        "  💹 Profit thresholds : Single {single} • Portfolio {portfolio}   [{src}]".format(
            single=_fmt_usd(prof_map.get("pos")),
            portfolio=_fmt_usd(prof_map.get("pf")),
            src=(prof_src or "unknown").upper(),
        )
    )
    _info(profit_line)
    print(profit_line, flush=True)


def emit_thresholds_trace(dl) -> None:
    """Emit FILE/DB/ENV provenance table when SONIC_THRESH_TRACE=1."""

    if os.getenv("SONIC_THRESH_TRACE", "0") != "1":
        return

    logger = logging.getLogger("SonicMonitor")
    _info = logger.info

    file_map, db_map, env_map, _liq_src = _resolve_liquid_sources(dl)
    prof_map, _prof_src = _resolve_profit_sources(dl)

    def _pick(sym: str) -> tuple[Optional[float], str]:
        if file_map.get(sym) is not None:
            return file_map[sym], "FILE"
        if db_map.get(sym) is not None:
            return db_map[sym], "DB"
        if env_map.get(sym) is not None:
            return env_map[sym], "ENV"
        return None, "—"

    rows: List[Dict[str, str]] = []
    for sym, label in (
        ("BTC", "₿ BTC • 💧 Liquid"),
        ("ETH", "Ξ ETH • 💧 Liquid"),
        ("SOL", "◎ SOL • 💧 Liquid"),
    ):
        chosen, src = _pick(sym)
        rows.append(
            {
                "metric": label,
                "file": _fmt_num(file_map.get(sym)),
                "db": _fmt_num(db_map.get(sym)),
                "env": _fmt_num(env_map.get(sym)),
                "used": _fmt_num(chosen),
                "src": src,
            }
        )

    rows.append(
        {
            "metric": "👤 Single • 💹 Profit",
            "file": "—",
            "db": _fmt_usd(prof_map.get("pos")),
            "env": "—",
            "used": _fmt_usd(prof_map.get("pos")),
            "src": "DB" if prof_map.get("pos") is not None else "—",
        }
    )
    rows.append(
        {
            "metric": "🧺 Portfolio • 💹 Profit",
            "file": "—",
            "db": _fmt_usd(prof_map.get("pf")),
            "env": "—",
            "used": _fmt_usd(prof_map.get("pf")),
            "src": "DB" if prof_map.get("pf") is not None else "—",
        }
    )

    title = "🔎 Threshold Resolution (why these numbers)"
    _info(title)
    print(title, flush=True)

    try:
        rich_console = importlib.import_module("rich.console")
        rich_table = importlib.import_module("rich.table")
        rich_box = importlib.import_module("rich.box")
        Console = getattr(rich_console, "Console")
        Table = getattr(rich_table, "Table")
        box = getattr(rich_box, "SIMPLE_HEAVY")

        tbl = Table(show_header=True, show_edge=True, box=box, pad_edge=False)
        tbl.add_column("Metric", justify="left", no_wrap=True)
        tbl.add_column("FILE", justify="right")
        tbl.add_column("DB", justify="right")
        tbl.add_column("ENV", justify="right")
        tbl.add_column("→ Used", justify="right")
        tbl.add_column("Source", justify="left")

        for row in rows:
            tbl.add_row(row["metric"], row["file"], row["db"], row["env"], row["used"], row["src"])

        Console().print(tbl)
        return
    except Exception:
        pass

    hdr = "Metric                          FILE        DB        ENV        → Used     Source"
    print(hdr)
    print("—" * len(hdr))
    for row in rows:
        print(
            f"{row['metric']:<30} {row['file']:>10} {row['db']:>10} {row['env']:>10}   {row['used']:>10}   {row['src']}"
        )


def _build_eval_rows(dl, csum: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str, str]:
    file_map, db_map, env_map, liq_src_hint = _resolve_liquid_sources(dl)

    def _pick_thr(sym: str) -> tuple[Optional[float], str]:
        if file_map.get(sym) is not None:
            return file_map[sym], "file"
        if db_map.get(sym) is not None:
            return db_map[sym], "db"
        if env_map.get(sym) is not None:
            return env_map[sym], "env"
        return None, "unknown"

    liq_thr_map: Dict[str, Optional[float]] = {}
    liq_src_per_sym: Dict[str, str] = {}
    liq_src_type = liq_src_hint
    for sym in ("BTC", "ETH", "SOL"):
        thr, src = _pick_thr(sym)
        liq_thr_map[sym] = thr
        liq_src_per_sym[sym] = src
        if liq_src_type == "unknown" and src != "unknown":
            liq_src_type = src
    if liq_src_type == "unknown" and liq_src_hint != "unknown":
        liq_src_type = liq_src_hint

    prof_map, prof_src_type = _resolve_profit_sources(dl)
    prof_single_thr = prof_map.get("pos")
    prof_port_thr = prof_map.get("pf")

    # Value source: snapshot table for this cycle if present, otherwise legacy positions.
    cycle_id = csum.get("cycle_id")
    nearest = _nearest_liq_from_db(dl, cycle_id)
    single_act, port_act = _profit_actuals_from_db(dl)

    rows: List[Dict[str, Any]] = []
    for sym, icon in (("BTC", "₿"), ("ETH", "Ξ"), ("SOL", "◎")):
        rows.append(
            {
                "metric": f"{icon} {sym} • 💧 Liquid",
                "kind": "liquid",
                "value": nearest.get(sym),
                "rule": "≤",
                "threshold": liq_thr_map.get(sym),
                "src": _src_label("snap" if cycle_id else "db", liq_src_per_sym.get(sym, liq_src_type)),
            }
        )

    rows.append(
        {
            "metric": "👤 Single • 💹 Profit",
            "kind": "profit",
            "value": single_act,
            "rule": "≥",
            "threshold": prof_single_thr,
            "src": _src_label("db", prof_src_type),
        }
    )
    rows.append(
        {
            "metric": "🧺 Portfolio • 💹 Profit",
            "kind": "profit",
            "value": port_act,
            "rule": "≥",
            "threshold": prof_port_thr,
            "src": _src_label("db", prof_src_type),
        }
    )
    return rows, liq_src_type, prof_src_type


def emit_evaluations_table(dl, csum: Dict[str, Any], ts_label: Optional[str] = None) -> None:
    if os.getenv("SONIC_SHOW_THRESHOLDS", "1") == "0":
        return

    logger = logging.getLogger("SonicMonitor")
    _info = logger.info

    title = "🧭  Monitor Evaluations"
    if ts_label:
        title += f" — last cycle {ts_label}"
    _info(title)
    print(title, flush=True)

    rows, _, _ = _build_eval_rows(dl, csum)
    emit_thresholds_trace(dl)

    try:
        rich_console = importlib.import_module("rich.console")
        rich_table = importlib.import_module("rich.table")
        rich_box = importlib.import_module("rich.box")
        Console = getattr(rich_console, "Console")
        Table = getattr(rich_table, "Table")
        box = getattr(rich_box, "SIMPLE_HEAVY")

        tbl = Table(show_header=True, show_edge=True, box=box, pad_edge=False)
        tbl.add_column("Metric", justify="left", no_wrap=True)
        tbl.add_column("Value", justify="right")
        tbl.add_column("Rule", justify="center")
        tbl.add_column("Threshold", justify="right")
        tbl.add_column("Result", justify="left", no_wrap=True)
        tbl.add_column("Source (V / T)", justify="left", no_wrap=True)

        for r in rows:
            if r["kind"] == "liquid":
                val = _fmt_num(r["value"])
                thr = _fmt_num(r["threshold"])
            else:
                val = _fmt_usd(r["value"])
                thr = _fmt_usd(r["threshold"])
            res = _classify_result(r["kind"], r["value"], r["threshold"])
            tbl.add_row(r["metric"], val, r["rule"], thr, res, r["src"])

        Console().print(tbl)
        return
    except Exception:
        pass

    METRIC_W = 26
    VAL_W = 12
    RULE_W = 3
    THR_W = 12
    RES_W = 13
    SRC_W = 18
    top = "┌" + "─" * METRIC_W + "┬" + "─" * VAL_W + "┬" + "─" * RULE_W + "┬" + "─" * THR_W + "┬" + "─" * RES_W + "┬" + "─" * SRC_W + "┐"
    header = (
        f"│ {'Metric':<{METRIC_W}}│ {'Value':>{VAL_W}}│{'Rule':^{RULE_W}}│ {'Threshold':>{THR_W-1}}│ {'Result':<{RES_W-1}}│ {'Source (V / T)':<{SRC_W-1}}│"
    )
    sep = "├" + "─" * METRIC_W + "┼" + "─" * VAL_W + "┼" + "─" * RULE_W + "┼" + "─" * THR_W + "┼" + "─" * RES_W + "┼" + "─" * SRC_W + "┤"
    bot = "└" + "─" * METRIC_W + "┴" + "─" * VAL_W + "┴" + "─" * RULE_W + "┴" + "─" * THR_W + "┴" + "─" * RES_W + "┴" + "─" * SRC_W + "┘"
    _info(top)
    print(top)
    _info(header)
    print(header)
    _info(sep)
    print(sep)

    def _row(metric_label: str, actual_s: str, rule: str, thr_s: str, result: str, src_label: str) -> str:
        return f"│ {metric_label:<{METRIC_W-1}}│{actual_s:>{VAL_W}}│{rule:^{RULE_W}}│{thr_s:>{THR_W}}│ {result:<{RES_W-1}}│ {src_label:<{SRC_W-1}}│"

    for r in rows:
        if r["kind"] == "liquid":
            val = _fmt_num(r["value"])
            thr = _fmt_num(r["threshold"])
        else:
            val = _fmt_usd(r["value"])
            thr = _fmt_usd(r["threshold"])
        res = _classify_result(r["kind"], r["value"], r["threshold"])
        line = _row(r["metric"], val, r["rule"], thr, res, r["src"])
        _info(line)
        print(line)

    _info(bot)
    print(bot, flush=True)

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

    prices_top3 = csum.get("prices_top3", [])
    price_ages = csum.get("price_ages")
    if prices_top3:
        # pass ages if available; helper tolerates missing/None
        print(
            "   💰 Prices   : "
            + _fmt_prices_line(prices_top3, price_ages, enable_color),
            flush=True,
        )
    else:
        print("   💰 Prices   : –", flush=True)
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
            f.write(_json.dumps(out, ensure_ascii=False) + "\n")
    except Exception:
        pass

__all__ = [
    "StrictWhitelistFilter",
    "install_strict_console_filter",
    "neuter_legacy_console_logger",
    "silence_legacy_console_loggers",
    "emit_compact_cycle",
    "emit_evaluations_table",
    "emit_sources_line",
    "emit_json_summary",
    "emit_thresholds_panel",
]
