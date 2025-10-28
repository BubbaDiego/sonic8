from __future__ import annotations

import importlib
import json as _json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Per-cycle print memo: ensures we print certain blocks only once per cycle
# ---------------------------------------------------------------------------
_PRINT_MEMO: dict[str, Set[str]] = {}


def _cycle_key(csum: dict | None) -> str:
    """Best-effort cycle key: use cycle/summary identifiers when available."""

    if isinstance(csum, dict):
        for field in ("cycle_id", "cycle_num"):
            value = csum.get(field)
            if value not in (None, ""):
                return str(value)

        tokens: list[str] = []
        try:
            positions_meta = csum.get("positions") if isinstance(csum.get("positions"), dict) else None
            if isinstance(positions_meta, dict):
                ts = positions_meta.get("ts")
                if ts not in (None, ""):
                    tokens.append(str(ts))
                size = positions_meta.get("size")
                if size is None and isinstance(positions_meta.get("rows"), list):
                    size = len(positions_meta.get("rows") or [])
                if size not in (None, ""):
                    tokens.append(f"pos#{size}")

            prices_meta = csum.get("prices") if isinstance(csum.get("prices"), dict) else None
            if isinstance(prices_meta, dict):
                ts = prices_meta.get("ts")
                if ts not in (None, ""):
                    tokens.append(str(ts))
                size = prices_meta.get("size")
                if size is None and isinstance(prices_meta.get("rows"), list):
                    size = len(prices_meta.get("rows") or [])
                if size not in (None, ""):
                    tokens.append(f"px#{size}")
        except Exception:
            tokens = []

        if tokens:
            return "fallback:" + "/".join(tokens)

    return f"fallback:{id(csum)}"


def _printed_once(flag: str, csum: dict | None) -> bool:
    """Return True if flag already printed for this cycle; mark it otherwise."""

    key = _cycle_key(csum)
    flags = _PRINT_MEMO.get(key)
    if flags is None:
        if len(_PRINT_MEMO) > 4:
            for stale_key in list(_PRINT_MEMO.keys())[:-2]:
                _PRINT_MEMO.pop(stale_key, None)
        flags = _PRINT_MEMO.setdefault(key, set())

    if flag in flags:
        return True

    flags.add(flag)
    return False

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

    # --- Drop ALL legacy DEBUG[...] chatter (logger + stray prints) ---
    _dbg_re = re.compile(r"\bDEBUG\s*(?:\[|:)", re.IGNORECASE)

    class _DropDebugFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            try:
                msg = record.getMessage() or ""
                if _dbg_re.search(msg):
                    return False
            except Exception:
                return True
            return True

    logger.addFilter(_DropDebugFilter())

    class _StdoutDropDebug:
        def __init__(self, stream):
            self._s = stream

        def write(self, s):
            if _dbg_re.search(str(s) or ""):
                return
            self._s.write(s)

        def flush(self):
            try:
                self._s.flush()
            except Exception:
                pass

        def isatty(self):
            return getattr(self._s, "isatty", lambda: False)()

    if not isinstance(sys.stdout, _StdoutDropDebug):
        sys.stdout = _StdoutDropDebug(sys.stdout)
    if not isinstance(sys.stderr, _StdoutDropDebug):
        sys.stderr = _StdoutDropDebug(sys.stderr)

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

def _section_banner(text: str, *, indent: str = "", left: int = 22, right: int = 22) -> str:
    """Return a single-line hyphen banner like:
       ----------------------  <text>  ----------------------"""
    return f"{indent}{'-'*left} {text} {'-'*right}"


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


def _fmt_usd_signed(v: Optional[float]) -> str:
    base = _fmt_usd(v)
    if base == "—":
        return base
    try:
        val = float(v) if v is not None else None
    except Exception:
        val = None
    if val is not None and val > 0 and base.startswith("$"):
        return "$+" + base[1:]
    return base


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    getter = getattr(row, "get", None)
    if getter:
        try:
            return getter(key, default)
        except Exception:
            pass
    keys = getattr(row, "keys", None)
    if callable(keys):
        try:
            if key in keys():
                return row[key]
        except Exception:
            pass
    try:
        return row[key]  # type: ignore[index]
    except Exception:
        return default


def _normalize_rows(container: Any) -> List[Any]:
    if not container:
        return []
    data = container
    if isinstance(container, dict):
        data = container.get("rows") or container.get("data") or []
    if isinstance(data, list):
        return data
    if isinstance(data, tuple):
        return list(data)
    if isinstance(data, (str, bytes)):
        return []
    try:
        return list(data)
    except Exception:
        return []


def _bar(util: Optional[float], width: int = 10) -> Tuple[str, str]:
    """Return (bar, label) where util is 0..1 (None => n/a)."""
    if util is None or util < 0 or not (util == util):  # NaN guard
        return "░" * width, "n/a"
    util = max(0.0, util)
    fill = min(width, int(round(util * width)))
    return "█" * fill + "░" * (width - fill), f"{int(round(util * 100))}%"


def _nearest_liq_from_db(dl, cycle_id: Optional[str] = None) -> Dict[str, Optional[float]]:
    """
    Minimum absolute liquidation distance per asset.
    Snapshot path (sonic_positions): 'liq_dist' preferred, fallback to 'liquidation_distance'.
    Legacy runtime path (positions):  'liquidation_distance' preferred, fallback to 'liq_dist'.
    """
    out: Dict[str, Optional[float]] = {}
    try:
        cur = dl.db.get_cursor()
        if not cur:
            return out
        if cycle_id:
            has_liq = False
            try:
                cur.execute("PRAGMA table_info(sonic_positions)")
                has_liq = any(str(r[1]).lower() == "liq_dist" for r in (cur.fetchall() or []))
            except Exception:
                has_liq = False
            col = "liq_dist" if has_liq else "liquidation_distance"
            cur.execute(
                f"SELECT asset, MIN(ABS({col})) AS min_dist FROM sonic_positions WHERE cycle_id = ? GROUP BY asset",
                (cycle_id,),
            )
        else:
            try:
                cur.execute(
                    """
                    SELECT asset_type, MIN(ABS(liquidation_distance)) AS min_dist
                      FROM positions
                     WHERE status='ACTIVE'
                    GROUP BY asset_type
                    """
                )
            except Exception:
                cur.execute(
                    """
                    SELECT asset_type, MIN(ABS(liq_dist)) AS min_dist
                      FROM positions
                     WHERE status='ACTIVE'
                    GROUP BY asset_type
                    """
                )
        rows = cur.fetchall() or []
        for r in rows:
            asset = (
                r["asset"] if hasattr(r, "keys") and "asset" in r.keys()
                else (r["asset_type"] if hasattr(r, "keys") and "asset_type" in r.keys() else r[0])
            ) or ""
            val = (r["min_dist"] if "min_dist" in getattr(r, "keys", lambda: [])() else r[1])
            out[str(asset).upper()] = _num(val, None)
        return out
    except Exception:
        return out


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


# ---------- Positions rows (snapshot-first) ----------
def _probing_table_cols(cur, table: str) -> set:
    try:
        cur.execute(f"PRAGMA table_info({table})")
        return {str(r[1]) for r in (cur.fetchall() or [])}
    except Exception:
        return set()


def _fetch_positions_rows(dl, cycle_id: Optional[str]) -> List[Dict[str, Any]]:
    """
    Return a list of normalized position dicts for the current cycle, snapshot-first.
    Unified fields: asset, side, value, pnl, lev, liq, travel
    """

    rows: List[Dict[str, Any]] = []
    try:
        cur = dl.db.get_cursor()
        if not cur:
            return rows

        def _pick(cols: set, choices: List[str]) -> str:
            for choice in choices:
                if choice in cols:
                    return choice
            return "NULL"

        def _query_for(table: str, where_sql: str, where_args: tuple) -> None:
            cols = _probing_table_cols(cur, table)
            asset = _pick(cols, ["asset", "asset_type", "symbol"]) + " AS asset"
            side = _pick(cols, ["side", "position_type"]) + " AS side"
            value = _pick(cols, ["value_usd", "exposure_usd", "position_value_usd"]) + " AS value"
            pnl = _pick(cols, ["pnl", "pnl_after_fees_usd", "pnl_usd"]) + " AS pnl"
            lev = _pick(cols, ["leverage"]) + " AS lev"
            liq = _pick(cols, ["liq_dist", "liquidation_distance"]) + " AS liq"
            travel = _pick(cols, ["travel_pct", "travel_percent"]) + " AS travel"
            sql = (
                f"SELECT {asset}, {side}, {value}, {pnl}, {lev}, {liq}, {travel}"
                f" FROM {table} {where_sql}"
            )
            cur.execute(sql, where_args)
            for record in (cur.fetchall() or []):
                asset_val, side_val, value_val, pnl_val, lev_val, liq_val, travel_val = record

                def _f(x):
                    try:
                        return float(x)
                    except Exception:
                        return None

                rows.append(
                    {
                        "asset": str(asset_val).upper() if asset_val is not None else "?",
                        "side": str(side_val).upper() if side_val is not None else "?",
                        "value": _f(value_val) or 0.0,
                        "pnl": _f(pnl_val) or 0.0,
                        "lev": _f(lev_val),
                        "liq": _f(liq_val),
                        "travel": _f(travel_val),
                    }
                )

        if cycle_id:
            _query_for("sonic_positions", "WHERE cycle_id = ?", (cycle_id,))
        else:
            _query_for("positions", "WHERE status='ACTIVE'", ())

        return rows
    except Exception:
        return rows


# ---------- Positions & Hedges compact helpers ----------
def _read_positions_compact(dl, cycle_id: Optional[str]) -> Dict[str, Any]:
    """Return {count, pnl_single_max, pnl_portfolio_sum} using snapshot first."""
    out = {"count": 0, "pnl_single_max": 0.0, "pnl_portfolio_sum": 0.0}
    if dl is None:
        return out
    try:
        db = getattr(dl, "db", None)
        cur = db.get_cursor() if db else None
        if not cur:
            return out
        pnl_field = "pnl_after_fees_usd"
        if cycle_id:
            cur.execute("SELECT COUNT(*) FROM sonic_positions WHERE cycle_id = ?", (cycle_id,))
            row = cur.fetchone()
            if row is not None:
                try:
                    out["count"] = int(row[0])
                except Exception:
                    out["count"] = int(_row_get(row, 0, 0) or 0)
            try:
                cur.execute("SELECT pnl FROM sonic_positions WHERE cycle_id = ?", (cycle_id,))
                pnl_field = "pnl"
            except Exception:
                cur.execute(
                    "SELECT pnl_after_fees_usd FROM sonic_positions WHERE cycle_id = ?",
                    (cycle_id,),
                )
        else:
            cur.execute("SELECT COUNT(*) FROM positions WHERE status='ACTIVE'")
            row = cur.fetchone()
            if row is not None:
                try:
                    out["count"] = int(row[0])
                except Exception:
                    out["count"] = int(_row_get(row, 0, 0) or 0)
            try:
                cur.execute(
                    "SELECT pnl_after_fees_usd FROM positions WHERE status='ACTIVE'"
                )
            except Exception:
                cur.execute("SELECT pnl FROM positions WHERE status='ACTIVE'")
                pnl_field = "pnl"
        vals: List[float] = []
        for rec in cur.fetchall() or []:
            val = _row_get(rec, pnl_field, _row_get(rec, 0))
            try:
                num = float(val)
            except Exception:
                continue
            if num > 0:
                vals.append(num)
        out["pnl_single_max"] = max(vals) if vals else 0.0
        out["pnl_portfolio_sum"] = sum(vals) if vals else 0.0
    except Exception:
        return out
    return out


def _read_hedges_compact(dl, cycle_id: Optional[str]) -> Dict[str, Any]:
    """Return {planned, active, errors, strategy?} using sonic_hedges snapshot if present."""
    out = {"planned": 0, "active": 0, "errors": 0, "strategy": None}
    if dl is None:
        return out
    try:
        db = getattr(dl, "db", None)
        cur = db.get_cursor() if db else None
        if not cur:
            return out
        if cycle_id:
            cur.execute(
                "SELECT status, COUNT(1) FROM sonic_hedges WHERE cycle_id = ? GROUP BY status",
                (cycle_id,),
            )
        else:
            cur.execute("SELECT status, COUNT(1) FROM hedges GROUP BY status")
        for status, cnt in cur.fetchall() or []:
            s = str(status).lower()
            if "plan" in s:
                out["planned"] = int(cnt or 0)
            elif "active" in s:
                out["active"] = int(cnt or 0)
            elif "err" in s or "fail" in s:
                out["errors"] = int(cnt or 0)
        try:
            sysvars = getattr(dl, "system", None)
            cfg = sysvars.get_var("market_monitor") if sysvars else {}
            if cfg:
                out["strategy"] = cfg.get("rearm") or cfg.get("strategy") or out["strategy"]
        except Exception:
            pass
    except Exception:
        return out
    return out


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

    lm_file: Dict[str, Any] = {}
    if isinstance(file_json, dict):
        lm_file = _as_dict(
            file_json.get("liquid_monitor")
            or file_json.get("liquidation_monitor")
            or file_json.get("liquid")
            or {}
        )
    if (not lm_file) and gconf and hasattr(gconf, "get"):
        lm_file = _as_dict(gconf.get("liquid_monitor") or gconf.get("liquid") or {})

    thr_map = _as_dict(lm_file.get("thresholds") or {})
    glob = _num(lm_file.get("threshold_percent") or lm_file.get("percent"))
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
    """
    Returns ({'pos': x, 'pf': y}, chosen_source).
    Profit thresholds live in DB system vars; accept modern and legacy shapes.
    """

    try:
        sysvars = getattr(dl, "system", None)
    except Exception:
        sysvars = None

    try:
        pm = _as_dict(sysvars.get_var("profit_monitor") if sysvars else {})
    except Exception:
        pm = {}

    pos: Optional[float] = None
    pf: Optional[float] = None

    if pm:
        pos = _num(pm.get("position_profit_usd") or pm.get("single_usd") or pm.get("pos"))
        pf = _num(pm.get("portfolio_profit_usd") or pm.get("total_usd") or pm.get("pf"))

    if sysvars:
        if pos is None:
            try:
                pos = _num(sysvars.get_var("profit_position_threshold"))
            except Exception:
                pass
        if pos is None:
            try:
                pos = _num(sysvars.get_var("profit_threshold"))
            except Exception:
                pass
        if pos is None:
            try:
                pos = _num(sysvars.get_var("profit_badge_value"))
            except Exception:
                pass
        if pf is None:
            try:
                pf = _num(sysvars.get_var("profit_portfolio_threshold"))
            except Exception:
                pass
        if pf is None:
            try:
                pf = _num(sysvars.get_var("profit_total_threshold"))
            except Exception:
                pass
        if pf is None:
            try:
                pf = _num(sysvars.get_var("profit_total"))
            except Exception:
                pass

    if (pos is None or pf is None) and sysvars:
        try:
            mc = _as_dict(sysvars.get_var("monitor_config") or {})
        except Exception:
            mc = {}
        pm2 = _as_dict(mc.get("profit_monitor") or {})
        if pos is None:
            pos = _num(pm2.get("position_profit_usd"))
        if pf is None:
            pf = _num(pm2.get("portfolio_profit_usd"))

    src = "db" if (pos is not None or pf is not None) else "unknown"
    return {"pos": pos, "pf": pf}, src


def resolve_effective_thresholds(dl, csum: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Produce a single map of the exact thresholds the monitor should use this cycle.
    {'liquid': {'BTC':..., 'ETH':..., 'SOL':...}, 'profit': {'single':..., 'portfolio':...}, 'src': {...}}
    """

    json_path = os.getenv("SONIC_MONITOR_JSON", "")
    parsed = None
    if json_path:
        parsed, _ = _safe_json_load(json_path)

    file_map, db_map, env_map, _ = _resolve_liquid_sources(
        dl,
        parsed if isinstance(parsed, dict) else None,
    )

    liq: Dict[str, Optional[float]] = {}
    liq_src: Dict[str, str] = {}
    for sym in ("BTC", "ETH", "SOL"):
        if file_map.get(sym) is not None:
            liq[sym] = file_map[sym]
            liq_src[sym] = "FILE"
        elif db_map.get(sym) is not None:
            liq[sym] = db_map[sym]
            liq_src[sym] = "DB"
        elif env_map.get(sym) is not None:
            liq[sym] = env_map[sym]
            liq_src[sym] = "ENV"
        else:
            liq[sym] = None
            liq_src[sym] = "—"

    prof_map, prof_src = _resolve_profit_sources(dl)  # includes legacy banner fallbacks
    prof = {"single": prof_map.get("pos"), "portfolio": prof_map.get("pf")}

    return {"liquid": liq, "profit": prof, "src": {"liquid": liq_src, "profit": prof_src}}


def emit_positions_table(
    dl,
    csum: Dict[str, Any],
    ts_label: Optional[str] = None,
    *,
    indent: str = "",
) -> None:
    logger = logging.getLogger("SonicMonitor")
    _info = logger.info

    cycle_id: Optional[str] = None
    if isinstance(csum, dict):
        candidates: List[Any] = [csum.get("cycle_id")]
        positions_meta = csum.get("positions") if isinstance(csum.get("positions"), dict) else None
        if isinstance(positions_meta, dict):
            candidates.extend(
                [
                    positions_meta.get("cycle_id"),
                    positions_meta.get("snapshot_id"),
                ]
            )
        for candidate in candidates:
            if candidate not in (None, ""):
                cycle_id = str(candidate)
                break

    rows = _fetch_positions_rows(dl, cycle_id)
    if not rows:
        return

    def _liq_key(r: Dict[str, Any]) -> tuple:
        liq_val = r.get("liq")
        return (1, 0.0) if liq_val is None else (0, liq_val)

    def _value_for_sort(r: Dict[str, Any]) -> float:
        try:
            return float(r.get("value") or 0.0)
        except Exception:
            return 0.0

    rows.sort(key=lambda r: (_liq_key(r), -_value_for_sort(r)))

    def pnl_style(value: Optional[float]) -> str:
        if value is None:
            return ""
        return "green" if value > 0 else ("red" if value < 0 else "")

    def _fmt_lev(value: Optional[float]) -> str:
        if value is None:
            return "—"
        try:
            mag = abs(float(value))
            if mag >= 100:
                return f"{value:.0f}×"
            if mag >= 10:
                return f"{value:.1f}×"
            return f"{value:.2f}×"
        except Exception:
            return str(value)

    if not _printed_once("positions_header", csum):
        title_text = "📊  Positions  Snapshot"
        if ts_label:
            title_text += f" — {ts_label}"
        title = _section_banner(title_text, indent=indent)
        _info(title)
        print(title, flush=True)

    try:
        rich_console = importlib.import_module("rich.console")
        rich_table = importlib.import_module("rich.table")
        rich_box = importlib.import_module("rich.box")
        rich_padding = importlib.import_module("rich.padding")
        rich_text = importlib.import_module("rich.text")

        Console = getattr(rich_console, "Console")
        Table = getattr(rich_table, "Table")
        Padding = getattr(rich_padding, "Padding")
        box = getattr(rich_box, "SIMPLE_HEAVY")
        Text = getattr(rich_text, "Text")

        tbl = Table(show_header=True, show_edge=True, box=box, pad_edge=False)
        tbl.add_column("Asset", justify="left", no_wrap=True)
        tbl.add_column("Side", justify="left", no_wrap=True)
        tbl.add_column("Value", justify="right")
        tbl.add_column("PnL", justify="right")
        tbl.add_column("Lev", justify="right", no_wrap=True)
        tbl.add_column("Liq", justify="right", no_wrap=True)
        tbl.add_column("Travel", justify="right", no_wrap=True)

        for row in rows:
            pnl = row.get("pnl")
            tbl.add_row(
                str(row.get("asset", "?")),
                str(row.get("side", "?")),
                _fmt_usd(row.get("value")),
                Text(_fmt_usd(pnl), style=pnl_style(pnl)),
                _fmt_lev(row.get("lev")),
                _fmt_pct(row.get("liq")),
                _fmt_pct(row.get("travel")),
            )

        Console().print(Padding(tbl, (0, 0, 0, len(indent))))
        return
    except Exception:
        pass

    headers = ["Asset", "Side", "Value", "PnL", "Lev", "Liq", "Travel"]
    align = ["<", "<", ">", ">", ">", ">", ">"]
    data: List[List[str]] = []
    for row in rows:
        data.append(
            [
                str(row.get("asset", "?")),
                str(row.get("side", "?")),
                _fmt_usd(row.get("value")),
                _fmt_usd(row.get("pnl")),
                _fmt_lev(row.get("lev")),
                _fmt_pct(row.get("liq")),
                _fmt_pct(row.get("travel")),
            ]
        )

    widths = [len(h) for h in headers]
    for row in data:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def _format_row(parts: List[str]) -> str:
        formatted = []
        for idx, cell in enumerate(parts):
            width = widths[idx]
            align_mode = align[idx]
            formatted.append(f"{cell:{align_mode}{width}}")
        return indent + "│ " + " │ ".join(formatted) + " │"

    def _hline(left: str, mid: str, right: str) -> str:
        segments = ["─" * (w + 2) for w in widths]
        return indent + left + mid.join(segments) + right

    top = _hline("┌", "┬", "┐")
    sep = _hline("├", "┼", "┤")
    bottom = _hline("└", "┴", "┘")

    header_line = _format_row(headers)
    _info(top)
    print(top)
    _info(header_line)
    print(header_line)
    _info(sep)
    print(sep)

    for row in data:
        line = _format_row(row)
        _info(line)
        print(line)

    _info(bottom)
    print(bottom, flush=True)


def emit_thresholds_sync_step(dl, csum: dict | None = None) -> None:
    """Emit the always-on Sync Data thresholds snapshot."""

    if _printed_once("sync_thresholds", csum):
        return

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

    # ── Step C: quick schema check (accept modern + legacy shapes)
    if isinstance(parsed, dict):
        lm = (
            parsed.get("liquid_monitor")
            or parsed.get("liquidation_monitor")
            or parsed.get("liquid")
            or {}
        )
        if not isinstance(lm, dict):
            lm = {}
        thr_map = (
            lm.get("thresholds")
            or lm.get("thr")
            or {}
        )
        if not isinstance(thr_map, dict):
            thr_map = {}
        glob = lm.get("threshold_percent") or lm.get("percent")

        pm = parsed.get("profit_monitor") or parsed.get("profit") or {}
        if not isinstance(pm, dict):
            pm = {}
        pos = (
            pm.get("position_profit_usd")
            or pm.get("single_usd")
            or pm.get("pos")
        )
        pf = (
            pm.get("portfolio_profit_usd")
            or pm.get("total_usd")
            or pm.get("pf")
        )

        flags: List[str] = []
        flags.append(
            "liquid_monitor ✓"
            if (
                parsed.get("liquid_monitor")
                or parsed.get("liquidation_monitor")
                or parsed.get("liquid")
            )
            else "liquid_monitor ✗"
        )
        flags.append(
            "thresholds ✓"
            if (thr_map and isinstance(thr_map, dict)) or (glob is not None)
            else "thresholds ✗"
        )
        for sym in ("BTC", "ETH", "SOL"):
            has_sym = (sym in thr_map) or (glob is not None)
            flags.append(f"{sym} {'✓' if has_sym else '✗'}")

        flags.append(
            "profit_monitor ✓"
            if parsed.get("profit_monitor") or parsed.get("profit")
            else "profit_monitor ✗"
        )
        flags.append("pos ✓" if pos is not None else "pos ✗")
        flags.append("pf ✓" if pf is not None else "pf ✗")

        line = "  🔎 Schema check      : " + ", ".join(flags)
        _info(line)
        print(line, flush=True)

        try:
            def _norm(v: Any) -> str:
                if v is None:
                    return "—"
                try:
                    return f"{float(v):.2f}".rstrip("0").rstrip(".")
                except Exception:
                    return str(v)

            btc_v = thr_map.get("BTC") if thr_map else None
            eth_v = thr_map.get("ETH") if thr_map else None
            sol_v = thr_map.get("SOL") if thr_map else None
            norm_liq = "BTC {btc} • ETH {eth} • SOL {sol}".format(
                btc=_norm(btc_v if btc_v is not None else glob),
                eth=_norm(eth_v if eth_v is not None else glob),
                sol=_norm(sol_v if sol_v is not None else glob),
            )
            norm_prof = "Single {single} • Portfolio {portfolio}".format(
                single=(f"${int(float(pos))}" if pos is not None else "—"),
                portfolio=(f"${int(float(pf))}" if pf is not None else "—"),
            )
            line2 = (
                "  ↳ Normalized as     : "
                "liquid_monitor.thresholds → {liq} ; profit_monitor → {prof}".format(
                    liq=norm_liq,
                    prof=norm_prof,
                )
            )
            _info(line2)
            print(line2, flush=True)
        except Exception:
            pass

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


def _build_eval_rows(dl, csum: Dict[str, Any], eff: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str, str]:
    liq_thr_map: Dict[str, Optional[float]] = eff.get("liquid", {})
    liq_src_per_asset: Dict[str, str] = eff.get("src", {}).get("liquid", {})

    liq_src_type = "unknown"
    for sym in ("BTC", "ETH", "SOL"):
        sym_src = str(liq_src_per_asset.get(sym, "unknown"))
        if liq_src_type == "unknown" and sym_src.lower() not in {"unknown", "—"}:
            liq_src_type = sym_src.lower()

    prof_src_type = str(eff.get("src", {}).get("profit", "unknown"))
    prof_single_thr = eff.get("profit", {}).get("single")
    prof_port_thr = eff.get("profit", {}).get("portfolio")

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
                "src": _src_label(
                    "snap" if cycle_id else "db",
                    str(liq_src_per_asset.get(sym, "unknown")).lower(),
                ),
            }
        )

    rows.append(
        {
            "metric": "👤 Single • 💹 Profit",
            "kind": "profit",
            "value": single_act,
            "rule": "≥",
            "threshold": prof_single_thr,
            "src": _src_label("db", str(prof_src_type).lower()),
        }
    )
    rows.append(
        {
            "metric": "🧺 Portfolio • 💹 Profit",
            "kind": "profit",
            "value": port_act,
            "rule": "≥",
            "threshold": prof_port_thr,
            "src": _src_label("db", str(prof_src_type).lower()),
        }
    )
    return rows, liq_src_type, str(prof_src_type)


def emit_evaluations_table(
    dl,
    csum: Dict[str, Any],
    ts_label: Optional[str] = None,
    *,
    effective: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Console table: (Row 1) Title • (Row 2) Column headers • (Rows 3+) Data
    Uses rich.Table when available; falls back to ASCII.
    Liquid values/thresholds are numeric distances (no %); Profit uses $.
    """
    if os.getenv("SONIC_SHOW_THRESHOLDS", "1") == "0":
        return

    logger = logging.getLogger("SonicMonitor")

    INDENT = "  "
    title_text = "🧭 Monitor Evaluations"
    if ts_label:
        title_text += f" — last cycle {ts_label}"

    if effective is None:
        effective = resolve_effective_thresholds(dl, csum)

    rows, _, _ = _build_eval_rows(dl, csum, effective)
    emit_thresholds_trace(dl)

    try:
        rich_console = importlib.import_module("rich.console")
        rich_table = importlib.import_module("rich.table")
        rich_box = importlib.import_module("rich.box")
        rich_text = importlib.import_module("rich.text")
        rich_padding = importlib.import_module("rich.padding")
        Console = getattr(rich_console, "Console")
        Table = getattr(rich_table, "Table")
        box = getattr(rich_box, "SIMPLE_HEAVY")
        Text = getattr(rich_text, "Text")
        Padding = getattr(rich_padding, "Padding")

        tbl = Table(show_header=False, show_edge=True, box=box, pad_edge=False)
        tbl.add_column("Metric", justify="left", no_wrap=True)
        tbl.add_column("Value", justify="right")
        tbl.add_column("Rule", justify="center")
        tbl.add_column("Threshold", justify="right")
        tbl.add_column("Result", justify="left", no_wrap=True)
        tbl.add_column("Source (V / T)", justify="left", no_wrap=True)

        tbl.add_row(Text(title_text, style="bold"), "", "", "", "", "", end_section=True)
        tbl.add_row(
            Text("Metric", style="bold"),
            Text("Value", style="bold"),
            Text("Rule", style="bold"),
            Text("Threshold", style="bold"),
            Text("Result", style="bold"),
            Text("Source (V / T)", style="bold"),
            end_section=True,
        )

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
    title = (
        pad
        + f"│ {title_text:<{METRIC_W-1}}"
        + " "
        + f"│{'' :>{VAL_W}}│{'' :^{RULE_W}}│{'' :>{THR_W}}│{'' :<{RES_W}}│ {'' :<{SRC_W-1}}│"
    )
    sep = pad + "├" + "─" * METRIC_W + "┼" + "─" * VAL_W + "┼" + "─" * RULE_W + "┼" + "─" * THR_W + "┼" + "─" * RES_W + "┼" + "─" * SRC_W + "┤"
    header = pad + f"│ {'Metric':<{METRIC_W}}│ {'Value':>{VAL_W}}│{'Rule':^{RULE_W}}│ {'Threshold':>{THR_W-1}}│ {'Result':<{RES_W-1}}│ {'Source (V / T)':<{SRC_W-1}}│"
    bot = pad + "└" + "─" * METRIC_W + "┴" + "─" * VAL_W + "┴" + "─" * RULE_W + "┴" + "─" * THR_W + "┴" + "─" * RES_W + "┴" + "─" * SRC_W + "┘"

    logger.info(top)
    print(top)
    logger.info(title)
    print(title)
    logger.info(sep)
    print(sep)
    logger.info(header)
    print(header)
    logger.info(sep)
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
        logger.info(line)
        print(line)

    logger.info(bot)
    print(bot, flush=True)

# ───────────────────────── main compact renderer ─────────────────

def emit_compact_cycle(
    csum: Dict[str, Any],
    cyc_ms: int,
    interval: int,
    loop_counter: int,
    total_elapsed: float,
    sleep_time: float,
    dl: Any | None = None,
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
    cycle_id: Optional[str] = None
    if isinstance(csum, dict):
        cid = csum.get("cycle_id")
        if cid not in (None, ""):
            cycle_id = str(cid)

    pos_summary = _read_positions_compact(dl, cycle_id)
    pos_rows = _normalize_rows(positions)
    if (
        pos_rows
        and pos_summary.get("count", 0) == 0
        and float(pos_summary.get("pnl_single_max", 0.0) or 0.0) == 0.0
        and float(pos_summary.get("pnl_portfolio_sum", 0.0) or 0.0) == 0.0
    ):
        active_rows = [
            row
            for row in pos_rows
            if str((_row_get(row, "status", "ACTIVE") or "ACTIVE")).upper() in {"", "ACTIVE"}
        ]
        considered = active_rows or pos_rows
        positives: List[float] = []
        for row in considered:
            val = _row_get(row, "pnl_after_fees_usd", 0.0)
            try:
                num = float(val)
            except Exception:
                continue
            if num > 0:
                positives.append(num)
        pos_summary["count"] = len(considered)
        pos_summary["pnl_single_max"] = max(positives) if positives else 0.0
        pos_summary["pnl_portfolio_sum"] = sum(positives) if positives else 0.0

    hed_summary = _read_hedges_compact(dl, cycle_id)
    hed_rows = _normalize_rows(hedges)
    if (
        hed_rows
        and hed_summary.get("planned", 0) == 0
        and hed_summary.get("active", 0) == 0
        and hed_summary.get("errors", 0) == 0
    ):
        planned = active = errors = 0
        for row in hed_rows:
            status = str(_row_get(row, "status", "")).lower()
            if "plan" in status:
                planned += 1
            elif "active" in status:
                active += 1
            elif "err" in status or "fail" in status:
                errors += 1
        hed_summary["planned"] = planned
        hed_summary["active"] = active
        hed_summary["errors"] = errors
        if hed_summary.get("strategy") is None and isinstance(hedges, dict):
            strategy_hint = (
                hedges.get("strategy")
                or hedges.get("strategy_hint")
                or hedges.get("tag")
            )
            if strategy_hint:
                hed_summary["strategy"] = strategy_hint

    pf_total = float(pos_summary.get("pnl_portfolio_sum", 0.0) or 0.0)
    pos_line = (
        f"{int(pos_summary.get('count', 0) or 0)} active • PnL {_fmt_usd_signed(pf_total)} "
        f"(pos max {_fmt_usd_signed(pos_summary.get('pnl_single_max'))} / pf {_fmt_usd_signed(pf_total)})"
    )
    hed_line = (
        f"{int(hed_summary.get('planned', 0) or 0)} planned • "
        f"{int(hed_summary.get('active', 0) or 0)} active • "
        f"{int(hed_summary.get('errors', 0) or 0)} errors"
    )
    strategy_hint = hed_summary.get("strategy")
    if strategy_hint:
        hed_line += f"  (strategy={strategy_hint})"
    print("   📊 Positions: " + pos_line, flush=True)
    print("   🛡 Hedges   : " + hed_line, flush=True)

    # (UX) Sources line removed — Sync Data & Evaluations show provenance

    # (Alerts block removed — Evaluations table covers breach state)
    notif_line = csum.get("notifications_brief", "NONE (no_breach)")
    print(f"   📨 Notifications : {notif_line}")

    # (UX) Monitors rollup line removed — the Evaluations table supersedes it

    # (UX) End-of-cycle status line removed — keep only the other cycle header elsewhere

# ───────────────────── optional sources/jsonl ───────────────────

def emit_sources_line(sources: Dict[str, Any], label: str = "") -> None:
    """Legacy no-op retained for compatibility with older monitor builds."""
    # (UX) Sources line removed — Sync Data & Evaluations show provenance
    return

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
    "_section_banner",
    "emit_evaluations_table",
    "emit_positions_table",
    "resolve_effective_thresholds",
    "emit_sources_line",
    "emit_json_summary",
    "emit_thresholds_panel",
]
