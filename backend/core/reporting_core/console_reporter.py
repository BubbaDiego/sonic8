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


def install_compact_console_filter(enable_color: bool = True) -> None:
    """Install concise logging style and mute noisy modules."""

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    fmt = "%(message)s" if enable_color else "%(message)s"
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setFormatter(logging.Formatter(fmt))

    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)

    for name in ("ConsoleLogger", "console_logger", "LoggerControl", "werkzeug", "uvicorn.access", "fuzzy_wuzzy", "asyncio"):
        logging.getLogger(name).setLevel(logging.ERROR)

    # --- Drop all XCOM debug chatter (both logger and stray prints) ---
    class _DropXCOMFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            name = (record.name or "").lower()
            msg = ""
            try:
                msg = record.getMessage() or ""
            except Exception:
                pass
            if "xcom" in name and record.levelno <= logging.INFO:
                return False
            if msg.startswith("DEBUG[XCOM]"):
                return False
            return True

    logger.addFilter(_DropXCOMFilter())

    class _StdoutFilterXCOM:
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

    if not isinstance(sys.stdout, _StdoutFilterXCOM):
        sys.stdout = _StdoutFilterXCOM(sys.stdout)
    if not isinstance(sys.stderr, _StdoutFilterXCOM):
        sys.stderr = _StdoutFilterXCOM(sys.stderr)

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


def _safe_json_load(path: str) -> tuple[Optional[dict], Optional[str]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return _json.load(f), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


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
    file_json: Optional[dict] = None,
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

    # FILE (prefer explicit JSON if provided; fall back to loader global_config)
    if isinstance(file_json, dict) and "liquid_monitor" in file_json:
        lm_file = _as_dict(file_json.get("liquid_monitor"))
    else:
        lm_file = _as_dict(gconf.get("liquid_monitor") if hasattr(gconf, "get") else {})
    if (not lm_file) and isinstance(file_json, dict) and "liquidation_monitor" in file_json:
        lm_file = _as_dict(file_json.get("liquidation_monitor"))
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

    def _discover_json_path() -> str:
        path = os.getenv("SONIC_MONITOR_JSON", "").strip()
        if path:
            return path

        try:
            from backend.core.monitor_core.config_store import DEFAULT_JSON_PATH  # type: ignore

            if DEFAULT_JSON_PATH:
                return DEFAULT_JSON_PATH
        except Exception:
            pass

        here = Path(__file__).resolve()
        backend_dir = here.parents[2]
        modern = backend_dir / "config" / "monitor_config.json"
        legacy = backend_dir / "config" / "sonic_monitor_config.json"
        return str(modern if modern.exists() else legacy)

    json_path = _discover_json_path()
    jp = Path(json_path)
    try:
        exists = jp.exists()
        size = jp.stat().st_size if exists else 0
        mtime = (
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(jp.stat().st_mtime))
            if exists
            else "-"
        )
    except Exception:
        exists, size, mtime = False, 0, "-"

    # ── Step A: print path/existence
    json_line = (
        f"  📄 Config JSON path  : {json_path}  "
        + (f"[exists ✓, {size} bytes, mtime {mtime}]" if exists else "[missing ✗]")
    )
    _info(json_line)
    print(json_line, flush=True)

    # ── Step B: parse JSON for diagnostics
    parsed, parse_err = (_safe_json_load(json_path) if exists else (None, "missing"))
    if parse_err:
        line = f"  📥 Parse JSON        : ❌ {parse_err}"
    else:
        keys = ", ".join(sorted(parsed.keys())) if isinstance(parsed, dict) else "—"
        line = f"  📥 Parse JSON        : ✅ keys=({keys})"
    _info(line)
    print(line, flush=True)

    # ── Step C: quick schema check to aid operators
    if isinstance(parsed, dict):
        flags: List[str] = []
        flags.append(
            "liquid_monitor ✓" if "liquid_monitor" in parsed or "liquidation_monitor" in parsed else "liquid_monitor ✗"
        )
        lm = parsed.get("liquid_monitor") or parsed.get("liquidation_monitor") or {}
        if not isinstance(lm, dict):
            lm = {}
        flags.append(
            "thresholds ✓" if ("thresholds" in lm or "threshold_percent" in lm) else "thresholds ✗"
        )
        tm = lm.get("thresholds", {}) if isinstance(lm, dict) else {}
        for sym in ("BTC", "ETH", "SOL"):
            flags.append(f"{sym} {'✓' if (sym in tm if isinstance(tm, dict) else False) or 'threshold_percent' in lm else '✗'}")
        pm = parsed.get("profit_monitor", {})
        if not isinstance(pm, dict):
            pm = {}
        flags.append("profit_monitor ✓" if "profit_monitor" in parsed else "profit_monitor ✗")
        flags.append("pos ✓" if "position_profit_usd" in pm else "pos ✗")
        flags.append("pf ✓" if "portfolio_profit_usd" in pm else "pf ✗")
        line = "  🔎 Schema check      : " + ", ".join(flags)
        _info(line)
        print(line, flush=True)

    # ── Step D: resolve sources using parsed JSON (so FILE wins when present)
    file_map, db_map, env_map, _liq_src_overall = _resolve_liquid_sources(
        dl, parsed if isinstance(parsed, dict) else None
    )
    prof_map, prof_src = _resolve_profit_sources(dl)

    used_liq: Dict[str, Optional[float]] = {}
    used_srcs: Dict[str, str] = {}
    for sym in ("BTC", "ETH", "SOL"):
        if file_map.get(sym) is not None:
            used_liq[sym] = file_map[sym]
            used_srcs[sym] = "FILE"
        elif db_map.get(sym) is not None:
            used_liq[sym] = db_map[sym]
            used_srcs[sym] = "DB"
        elif env_map.get(sym) is not None:
            used_liq[sym] = env_map[sym]
            used_srcs[sym] = "ENV"
        else:
            used_liq[sym] = None
            used_srcs[sym] = "—"

    dt = time.perf_counter() - t0

    # ── Step E: final output lines
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
    if all(v is None for v in file_map.values()):
        hint = "  ↳ JSON thresholds not found in file; using DB/ENV fallbacks."
        _info(hint)
        print(hint, flush=True)
    elif missing:
        hint = "  ↳ JSON partial: missing → " + ", ".join(missing) + " (mixed with DB/ENV)."
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
    # Use the same resolution logic as the Sync step with per-asset provenance for the table.
    json_path = os.getenv("SONIC_MONITOR_JSON", "").strip()
    file_json, _ = (_safe_json_load(json_path) if json_path else (None, None))
    file_map, db_map, env_map, liq_src_hint = _resolve_liquid_sources(
        dl, file_json if isinstance(file_json, dict) else None
    )

    liq_thr_map: Dict[str, Optional[float]] = {}
    liq_src_per_asset: Dict[str, str] = {}
    liq_src_type = liq_src_hint
    for sym in ("BTC", "ETH", "SOL"):
        if file_map.get(sym) is not None:
            liq_thr_map[sym] = file_map[sym]
            liq_src_per_asset[sym] = "file"
        elif db_map.get(sym) is not None:
            liq_thr_map[sym] = db_map[sym]
            liq_src_per_asset[sym] = "db"
        elif env_map.get(sym) is not None:
            liq_thr_map[sym] = env_map[sym]
            liq_src_per_asset[sym] = "env"
        else:
            liq_thr_map[sym] = None
            liq_src_per_asset[sym] = "unknown"
        if liq_src_type == "unknown" and liq_src_per_asset[sym] != "unknown":
            liq_src_type = liq_src_per_asset[sym]
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
                # per-asset threshold source + value source (SNAP if we have cycle snapshot)
                "src": _src_label("snap" if cycle_id else "db", liq_src_per_asset.get(sym, "unknown")),
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

    INDENT = "  "
    title = INDENT + "🧭  Monitor Evaluations"
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
        rich_padding = importlib.import_module("rich.padding")
        Console = getattr(rich_console, "Console")
        Table = getattr(rich_table, "Table")
        box = getattr(rich_box, "SIMPLE_HEAVY")
        Padding = getattr(rich_padding, "Padding")

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

        Console().print(Padding(tbl, (0, 0, 0, len(INDENT))))
        return
    except Exception:
        pass

    METRIC_W = 26
    VAL_W = 12
    RULE_W = 3
    THR_W = 12
    RES_W = 13
    SRC_W = 18
    pad = INDENT
    top = pad + "┌" + "─" * METRIC_W + "┬" + "─" * VAL_W + "┬" + "─" * RULE_W + "┬" + "─" * THR_W + "┬" + "─" * RES_W + "┬" + "─" * SRC_W + "┐"
    header = pad + f"│ {'Metric':<{METRIC_W}}│ {'Value':>{VAL_W}}│{'Rule':^{RULE_W}}│ {'Threshold':>{THR_W-1}}│ {'Result':<{RES_W-1}}│ {'Source (V / T)':<{SRC_W-1}}│"
    sep = pad + "├" + "─" * METRIC_W + "┼" + "─" * VAL_W + "┼" + "─" * RULE_W + "┼" + "─" * THR_W + "┼" + "─" * RES_W + "┼" + "─" * SRC_W + "┤"
    bot = pad + "└" + "─" * METRIC_W + "┴" + "─" * VAL_W + "┴" + "─" * RULE_W + "┴" + "─" * THR_W + "┴" + "─" * RES_W + "┴" + "─" * SRC_W + "┘"
    _info(top)
    print(top)
    _info(header)
    print(header)
    _info(sep)
    print(sep)

    def _row(metric_label: str, actual_s: str, rule: str, thr_s: str, result: str, src_label: str) -> str:
        return pad + f"│ {metric_label:<{METRIC_W-1}}│{actual_s:>{VAL_W}}│{rule:^{RULE_W}}│{thr_s:>{THR_W}}│ {result:<{RES_W-1}}│ {src_label:<{SRC_W-1}}│"

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

    # (Alerts block removed — Evaluations table covers breach state)
    notif_line = csum.get("notifications_brief", "NONE (no_breach)")
    print(f"   📨 Notifications : {notif_line}")

    # (UX) Monitors rollup line removed — the Evaluations table supersedes it

    # (UX) End-of-cycle status line removed — keep only the other cycle header elsewhere

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
    "install_compact_console_filter",
    "neuter_legacy_console_logger",
    "silence_legacy_console_loggers",
    "emit_compact_cycle",
    "emit_evaluations_table",
    "emit_sources_line",
    "emit_json_summary",
    "emit_thresholds_panel",
]
