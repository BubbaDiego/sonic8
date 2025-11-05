# backend/core/monitor_core/sonic_monitor.py
# JSON-ONLY Sonic Monitor runner (single source of truth: backend/config/sonic_monitor_config.json)

from __future__ import annotations

import json
import os
import os as _os  # safe alias; we'll use _os.getenv in runtime sections
import re
import sys
import asyncio
import logging
import time
from contextlib import nullcontext
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Callable, Iterable

from backend.core.config_core.sonic_config_bridge import get_xcom_live
from backend.core.reporting_core.spinner import spin_progress, style_for_cycle

DEBUG_DUMP_SNAPSHOT = True


def _dump_cycle_snapshot(cycle_snapshot: dict | None, *, title: str = "CYCLE SNAPSHOT") -> None:
    """Pretty-print the snapshot (focused on 'monitors') for one cycle."""
    try:
        import json as _json

        snap = cycle_snapshot or {}
        payload = {
            "as_of": snap.get("as_of"),
            "keys": sorted(list(snap.keys())),
            "monitors": snap.get("monitors", "(missing)"),
        }
        print(f"\n[DEBUG] ==== {title} ====")
        print(_json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        print("[DEBUG] =====================\n")
    except Exception as e:  # pragma: no cover - defensive debug helper
        print(f"[DEBUG] snapshot dump failed: {type(e).__name__}: {e}")

# ----- Handoff helpers (panels contract) -----
def _csum_prices(dl) -> dict:
    out = {}
    try:
        glp = getattr(dl, "get_latest_price", None)
        for sym in ("BTC", "ETH", "SOL"):
            cur = prev = None
            if callable(glp):
                info = glp(sym) or {}
                cur = info.get("current_price") or info.get("current") or info.get("price")
                prev = info.get("previous") or info.get("prev")
            out[sym] = {
                "current": float(cur) if cur is not None else None,
                "previous": float(prev) if prev is not None else None,
            }
    except Exception:
        pass
    return out


def _norm_row(r):
    return r if isinstance(r, dict) else getattr(r, "__dict__", {}) or {}


def _collect_positions_from_dl(dl):
    for root in ("positions", "portfolio", "cache"):
        holder = getattr(dl, root, None)
        if not holder:
            continue
        for name in ("active", "active_positions", "positions", "snapshot", "last_positions"):
            v = getattr(holder, name, None)
            if isinstance(v, list) and v:
                return [_norm_row(x) for x in v], f"dl.{root}.{name}"
            m = getattr(holder, name, None)
            if callable(m):
                try:
                    vv = m()
                    if isinstance(vv, list) and vv:
                        return [_norm_row(x) for x in vv], f"dl.{root}.{name}()"
                except Exception:
                    pass
    sys = getattr(dl, "system", None)
    if sys:
        for key in ("active_positions", "positions_snapshot", "last_positions"):
            try:
                vv = sys.get_var(key)
                if isinstance(vv, list) and vv:
                    return [_norm_row(x) for x in vv], f"dl.system[{key}]"
            except Exception:
                pass
    return [], "none"


def _collect_positions_from_db(dl):
    # very defensive generic query; adjust names if you have a formal manager
    try:
        cur = dl.db.get_cursor()
        if not cur:
            return [], "db:none"
        cur.execute(
            """
            SELECT *
            FROM positions
            WHERE status IN ('active','OPEN','open') OR status IS NULL
            ORDER BY COALESCE(updated_at, created_at) DESC
            LIMIT 200
        """
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return rows, "db:positions"
    except Exception as e:
        return [], f"db:error({e})"


def _csum_positions(dl):
    rows, src = _collect_positions_from_dl(dl)
    if rows:
        print(f"[HANDOFF] pos_rows={len(rows)} source={src}")
        return rows
    rows, src = _collect_positions_from_db(dl)
    print(f"[HANDOFF] pos_rows={len(rows)} source={src}")
    return rows


# ----- end handoff helpers -----

try:
    from colorama import Fore, Style  # optional dependency

    _CYAN = Style.BRIGHT + Fore.CYAN
    _RST = Style.RESET_ALL
except Exception:  # pragma: no cover - fallback when colorama is absent
    _CYAN = "\033[96m"  # bright cyan ANSI
    _RST = "\033[0m"

# ── ensure absolute imports resolve when launching this file directly ─────────
if __package__ in (None, ""):
    _REPO_ROOT = Path(__file__).resolve().parents[3]
    _BACKEND_ROOT = _REPO_ROOT / "backend"
    for _p in (str(_REPO_ROOT), str(_BACKEND_ROOT)):
        if _p not in sys.path:
            sys.path.insert(0, _p)

# ── dotenv bootstrap (nice-to-have; will not crash if missing) ───────────────
def _resolve_and_load_env() -> str | None:
    try:
        from dotenv import load_dotenv, find_dotenv  # type: ignore
    except Exception:
        return None

    here = Path(__file__).resolve()
    repo_root = here.parents[3] if len(here.parents) >= 4 else Path.cwd()

    candidates: list[Path] = []
    explicit = _os.getenv("SONIC_ENV_PATH")
    if explicit:
        candidates.append(Path(explicit))
    candidates.extend([
        repo_root / ".env",
        repo_root / "backend" / ".env",
        Path.cwd() / ".env",
    ])

    chosen: Path | None = None
    for path_candidate in candidates:
        try:
            if path_candidate and path_candidate.exists():
                chosen = path_candidate
                break
        except Exception:
            pass

    if chosen is None:
        try:
            found = find_dotenv(usecwd=True)
            if found:
                chosen = Path(found)
        except Exception:
            chosen = None

    if chosen is not None:
        try:
            load_dotenv(dotenv_path=str(chosen), override=False)
            os.environ["SONIC_ENV_PATH_RESOLVED"] = str(chosen)
        except Exception:
            pass
        return str(chosen)
    return None


_env_used = _resolve_and_load_env()


def _step(label, fn, *args, **kwargs):
    t0 = time.perf_counter()
    try:
        return fn(*args, **kwargs)
    finally:
        dt = time.perf_counter() - t0
        print(f"[PERF] {label} took {dt:.2f}s")

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"
for _candidate in (REPO_ROOT, BACKEND_ROOT):
    _candidate_str = str(_candidate)
    if _candidate_str not in sys.path:
        sys.path.insert(0, _candidate_str)

# --- Hardening: avoid local-shadow pitfalls ---
try:
    from backend.data.data_locker import DataLocker as DL
except Exception:
    DL = None

try:
    from backend.data.locker_factory import get_locker
except Exception:
    def get_locker():  # fallback to DL if factory missing
        if DL:
            try:
                return DL.get_instance()
            except Exception:
                return DL("mother.db")
        return None

if DL is not None:
    DataLocker = DL  # type: ignore[assignment]
else:  # pragma: no cover
    class DataLocker:  # type: ignore[too-many-ancestors]
        pass

# ── JSON-ONLY helpers ────────────────────────────────────────────────────────
def _json_path() -> str:
    # the only monitor config file we accept
    return _os.getenv("SONIC_MONITOR_CONFIG_PATH") or str(
        Path(__file__).resolve().parents[2] / "config" / "sonic_monitor_config.json"
    )


def _expand_env(node):
    if isinstance(node, str):
        m = re.fullmatch(r"\$\{([^}]+)\}", node.strip())
        return _os.getenv(m.group(1), node) if m else node
    if isinstance(node, list):
        return [_expand_env(x) for x in node]
    if isinstance(node, dict):
        return {k: _expand_env(v) for k, v in node.items()}
    return node


def _load_json_only() -> Dict[str, Any]:
    path = _json_path()
    if not os.path.exists(path):
        print(f"❌ JSON not found: {path}")
        raise SystemExit(2)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle) or {}
        if not isinstance(raw, dict):
            print(f"❌ JSON root is not an object: {path}")
            raise SystemExit(2)
        return _expand_env(raw)
    except Exception as exc:
        print(f"❌ JSON load error ({path}): {exc.__class__.__name__}: {exc}")
        raise SystemExit(2)


CFG: Dict[str, Any] = _load_json_only()

MOTHER_DB_PATH = (
    (CFG.get("system_config") or {}).get("db_path")
    or _os.getenv("SONIC_DB_PATH")
    or str(Path(__file__).resolve().parents[2] / "mother.db")
)
MONITOR_NAME = "sonic_monitor"

dal = None
if get_locker:
    try:
        dal = get_locker()
    except Exception:
        dal = None
if dal is None and DL:
    _db_path = str(MOTHER_DB_PATH)
    try:
        dal = DL.get_instance(_db_path)
    except Exception:
        dal = DL(_db_path)

def _get(d: Dict[str, Any], *keys, default=None):
    cur = d
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key, default)
    return cur if cur is not None else default


def _require(path_desc: str, value, coerce=lambda x: x):
    if value is None or (isinstance(value, str) and not value.strip()):
        print(f"❌ JSON missing: {path_desc}")
        raise SystemExit(2)
    try:
        return coerce(value)
    except Exception:
        print(f"❌ JSON invalid type for {path_desc}: {value!r}")
        raise SystemExit(2)


# --- AUGMENT CSUM WITH PRICES & POSITIONS (PANELS CONTRACT) ---


# ── REQUIRED JSON FIELDS (single source of truth) ────────────────────────────
LOOP_SECONDS = _require(
    "system_config.sonic_loop_delay | monitor.loop_seconds",
    _get(CFG, "system_config", "sonic_loop_delay") or _get(CFG, "monitor", "loop_seconds"),
    coerce=lambda x: int(float(x)),
)

LIQ_THR = _require(
    "liquid.thresholds | (legacy) liquid_monitor.thresholds",
    _get(CFG, "liquid", "thresholds") or _get(CFG, "liquid_monitor", "thresholds"),
    coerce=lambda mapping: {str(k).upper(): float(v) for k, v in mapping.items()},
)
_liq_blast_cfg = _get(CFG, "liquid", "blast") or {}
LIQ_BLAST = {str(k).upper(): int(_liq_blast_cfg.get(k, 0)) for k in LIQ_THR.keys()}

PROFIT_POS = _require(
    "profit.position_usd",
    _get(CFG, "profit", "position_usd"),
    coerce=lambda x: int(float(x)),
)
PROFIT_PF = _require(
    "profit.portfolio_usd",
    _get(CFG, "profit", "portfolio_usd"),
    coerce=lambda x: int(float(x)),
)


# seed DB once so legacy readers behave like JSON (but JSON stays the source)
try:
    sysmgr = dal.system
    sysmgr.set_var("sonic_monitor_loop_time", LOOP_SECONDS)
    sysmgr.set_var("alert_thresholds", json.dumps({"thresholds": LIQ_THR, "blast": LIQ_BLAST}, separators=(",", ":")))
    sysmgr.set_var("profit_pos", PROFIT_POS)
    sysmgr.set_var("profit_pf", PROFIT_PF)
    sysmgr.set_var("profit_badge_value", PROFIT_PF)  # compat alias
except Exception as exc:
    print(f"⚠ DB seed from JSON failed: {exc}")

# ── public “cfg_*” getters the rest of the file uses ─────────────────────────
def cfg_loop_seconds(default: int | None = None) -> int:
    return LOOP_SECONDS if LOOP_SECONDS is not None else (default or 60)

def cfg_enabled(name: str, default: bool | None = True) -> bool | None:
    value = _get(CFG, "monitor", "enabled", name)
    return bool(value) if value is not None else default

def cfg_xcom_live(default: bool | None = True) -> bool | None:
    value = _get(CFG, "monitor", "xcom_live")
    return bool(value) if value is not None else default

def cfg_price_assets(default=None):
    assets = _get(CFG, "price", "assets")
    return assets if isinstance(assets, list) and assets else (default or ["BTC", "ETH", "SOL"])

def cfg_liquid_thresholds() -> dict:
    return dict(LIQ_THR)

def cfg_liquid_blast() -> dict:
    return dict(LIQ_BLAST)

def cfg_profit_thresholds() -> dict:
    return {"position_usd": PROFIT_POS, "portfolio_usd": PROFIT_PF}

# normalize asset list
def get_price_assets() -> list[str]:
    assets = cfg_price_assets()
    normalized: list[str] = []
    for asset in assets:
        if asset is None:
            continue
        text = str(asset).strip().upper()
        if text:
            normalized.append(text)
    return normalized or ["BTC", "ETH", "SOL"]

# Optional DB-stored monitor toggles are still honored if JSON lacks an explicit flag.
try:
    _db_monitor_cfg_raw = dal.system.get_var("sonic_monitor") if getattr(dal, "system", None) else {}
    _db_monitor_cfg = dict(_db_monitor_cfg_raw) if isinstance(_db_monitor_cfg_raw, Mapping) else {}
except Exception:
    _db_monitor_cfg = {}

_loop_from_cfg_raw = cfg_loop_seconds(None)
try:
    _LOOP_SECONDS_OVERRIDE = int(_loop_from_cfg_raw) if _loop_from_cfg_raw is not None else None
except Exception:
    _LOOP_SECONDS_OVERRIDE = None

_enabled_overrides_raw: dict[str, Any] = {
    "sonic": cfg_enabled("sonic", default=None),
    "liquid": cfg_enabled("liquid", default=None),
    "profit": cfg_enabled("profit", default=None),
    "market": cfg_enabled("market", default=None),
    "price": cfg_enabled("price", default=None),
}
if _enabled_overrides_raw.get("liquid") is None:
    _enabled_overrides_raw["liquid"] = _db_monitor_cfg.get("enabled_liquid")
if _enabled_overrides_raw.get("profit") is None:
    _enabled_overrides_raw["profit"] = _db_monitor_cfg.get("enabled_profit")
if _enabled_overrides_raw.get("market") is None:
    _enabled_overrides_raw["market"] = _db_monitor_cfg.get("enabled_market")

_ENABLED_OVERRIDES: dict[str, Optional[bool]] = {k: (None if v is None else bool(v)) for k, v in _enabled_overrides_raw.items()}

# ── imports that depend on paths already set ─────────────────────────────────
from backend.core.monitor_core.utils.console_title import set_console_title
from backend.core.cyclone_core.cyclone_engine import Cyclone
from backend.core.monitor_core.activity_logger import ActivityLogger
from backend.core.monitor_core.sonic_events import notify_listeners
from backend.core.monitor_core.inputs.position_monitor import collect_positions
from backend.core.reporting_core.task_events import task_start, task_end
from backend.core.reporting_core.positions_icons import compute_positions_icon_line, compute_from_list
from backend.core.reporting_core.console_reporter import (
    install_compact_console_filter,
    install_strict_console_filter,
    neuter_legacy_console_logger,
    silence_legacy_console_loggers,
    emit_json_summary,
)
# Use the 4-arg compact printer from console_lines to match our call site
from backend.core.reporting_core import console_lines as cl
from backend.core.reporting_core.sonic_reporting.sequencer import (
    render_startup_banner,
    render_cycle,
)
from backend.core.monitor_core.summary_helpers import (
    load_monitor_config_snapshot,
    build_sources_snapshot,
    build_alerts_detail,
)
from backend.core.reporting_core.summary_cache import (
    snapshot_into,
    set_hedges,
    set_positions_icon_line,
    set_prices,
    set_prices_reason,
)
from backend.core.reporting_core.alerts_formatter import compose_alerts_inline
from backend.data.dl_hedges import DLHedgeManager
from backend.models.monitor_status import MonitorStatus, MonitorType

DEFAULT_JSON_PATH = r"C:\sonic7\backend\config\sonic_monitor_config.json"


def _first_present(mapping: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in mapping:
            value = mapping.get(key)
            if value is not None and value != "":
                return value
    return None


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except Exception:
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        text = text.replace(",", "")
        if text.endswith("%"):
            text = text[:-1]
        try:
            return float(text)
        except Exception:
            return None
    try:
        return float(value)  # type: ignore[arg-type]
    except Exception:
        return None


def _normalize_pos_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    asset = _first_present(
        row,
        ("asset", "symbol", "ticker", "asset_type", "market", "pair"),
    )
    side = _first_present(
        row,
        ("side", "position_side", "position_type", "direction", "dir"),
    )
    value = _coerce_float(
        _first_present(
            row,
            (
                "value",
                "value_usd",
                "notional",
                "notional_usd",
                "size_usd",
                "size",
                "position_value",
                "position_value_usd",
                "usd_value",
                "gross_value",
                "market_value",
            ),
        )
    )
    pnl = _coerce_float(
        _first_present(
            row,
            (
                "pnl",
                "pnl_usd",
                "pnl_after_fees_usd",
                "profit",
                "profit_usd",
                "net_pnl_usd",
                "total_pnl_usd",
            ),
        )
    )
    lev = _coerce_float(
        _first_present(
            row,
            (
                "lev",
                "leverage",
                "leverage_ratio",
                "effective_leverage",
                "leverage_used",
            ),
        )
    )
    liq = _coerce_float(
        _first_present(
            row,
            (
                "liquidation_distance",
                "liq",
                "liq_dist",
                "liq_pct",
                "liq_percent",
                "liquidation",
                "liquidation_buffer",
                "liquidation_distance_pct",
            ),
        )
    )
    travel = _coerce_float(
        _first_present(
            row,
            ("travel", "move", "move_pct", "change_pct", "delta_pct", "pct_change"),
        )
    )

    normalized: Dict[str, Any] = {
        "asset": str(asset).upper() if asset else None,
        "side": str(side).upper() if side else None,
        "value": value,
        "pnl": pnl,
        "lev": lev,
        "liquidation_distance": liq,
        "travel": travel,
    }
    return normalized


def _normalize_pos_rows(rows: Iterable[Any]) -> list[dict]:
    normalized: list[dict] = []
    for row in rows:
        if isinstance(row, Mapping):
            mapping = row
        else:
            mapping = getattr(row, "__dict__", {}) or {}
            if not isinstance(mapping, Mapping):
                continue
        normalized_row = _normalize_pos_row(mapping)
        if any(value is not None for value in normalized_row.values()):
            normalized.append(normalized_row)
    return normalized


DEFAULT_INTERVAL = 60  # only used if JSON somehow lacks a loop value (we exit earlier)

CYCLONE_GROUP_LABEL = "cyclone_core"
CYCLONE_GROUPS = [
    "cyclone_engine",
    "Cyclone",
    "CycloneHedgeService",
    "CyclonePortfolioService",
    "CycloneAlertService",
    "CyclonePositionService",
    "PositionSyncService",
    "PositionCoreService",
    "PositionEnrichmentService",
    "AlertEvaluator",
    "AlertController",
    "AlertServiceManager",
    "DataLocker",
    "PriceSyncService",
    "DBCore",
    "Logger",
    "AlertUtils",
    "CalcServices",
    "LockerFactory",
    "HedgeManager",
    "CycleRunner",
    "ConsoleHelper",
]

REMAINING_CYCLONE_STEPS = [
    "check_jupiter_for_updates",
    "prune_stale_positions",
    "enrich_positions",
    "aggregate_positions",
    "update_evaluated_value",
    "create_market_alerts",
    "cleanse_ids",
    "link_hedges",
    "update_hedges",
]

_MONITOR_LABELS: Dict[MonitorType, str] = {
    MonitorType.SONIC: "Sonic",
    MonitorType.PRICE: "Price",
    MonitorType.POSITIONS: "Positions",
    MonitorType.XCOM: "XCom",
}

_MON_STATE: Dict[str, str] = {}
_ALERTS_STATE: Dict[str, Any] = {}
_ALERT_LIMITS: Dict[str, Any] = {}

# ── convenience ──────────────────────────────────────────────────────────────
def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None

def _profit_thresholds() -> tuple[Optional[float], Optional[float]]:
    cfg = _ALERT_LIMITS.get("profit_monitor") or {}
    pos = cfg.get("position_profit_usd") or cfg.get("position_usd")
    pf = cfg.get("portfolio_profit_usd") or cfg.get("portfolio_usd")
    return _safe_float(pos), _safe_float(pf)

def _liquid_threshold_for(asset: str) -> Optional[float]:
    section = _ALERT_LIMITS.get("liquid_monitor") or {}
    thresholds = section.get("thresholds") or {}
    if isinstance(thresholds, Mapping):
        raw = thresholds.get(asset.upper())
        return _safe_float(raw)
    return None

# ── alert state ingestion (profit/liquid) ────────────────────────────────────
def _ingest_alert_result(name: str, result: Mapping[str, Any]) -> None:
    if not result or result.get("skipped"):
        return

    if name == "profit_monitor":
        profit_state: Dict[str, Any] = {}

        max_profit = result.get("max_profit") or result.get("highest_single_profit")
        if max_profit is None:
            badge_val = None
            try:
                if getattr(dal, "system", None):
                    badge_val = dal.system.get_var("profit_badge_value")
            except Exception:
                badge_val = None
            max_profit = badge_val

        max_profit_val = _safe_float(max_profit)
        pos_thr, pf_thr = _profit_thresholds()
        if max_profit_val is not None:
            entry: Dict[str, Any] = {"value": max_profit_val, "breach": bool(pos_thr is not None and max_profit_val >= pos_thr)}
            if pos_thr is not None:
                entry["threshold"] = pos_thr
            profit_state["position"] = entry

        total_profit = _safe_float(result.get("total_profit"))
        if total_profit is not None:
            breach_pf = bool(pf_thr is not None and total_profit >= pf_thr)
            entry_pf: Dict[str, Any] = {"value": total_profit, "breach": breach_pf}
            if pf_thr is not None:
                entry_pf["threshold"] = pf_thr
            profit_state["portfolio"] = entry_pf

        if profit_state:
            _ALERTS_STATE["profit"] = profit_state
        else:
            _ALERTS_STATE.pop("profit", None)
        return

    if name == "liquid_monitor":
        details = result.get("details")
        rows: list[Dict[str, Any]] = []
        if isinstance(details, list):
            for item in details:
                if not isinstance(item, Mapping):
                    continue
                asset = str(item.get("asset") or item.get("symbol") or "").strip().upper()
                if not asset:
                    continue
                dist = _safe_float(item.get("dist_pct") or item.get("distance"))
                threshold = _safe_float(item.get("threshold"))
                if threshold is None:
                    threshold = _liquid_threshold_for(asset)
                breach = bool(item.get("breach"))
                entry_liq: Dict[str, Any] = {"asset": asset, "breach": breach}
                if threshold is not None:
                    entry_liq["threshold"] = threshold
                if dist is not None:
                    entry_liq["dist_pct"] = dist
                rows.append(entry_liq)

        if rows:
            _ALERTS_STATE["liquid"] = rows
        else:
            _ALERTS_STATE.pop("liquid", None)


def _normalize_profit_entry(
    raw_entry: Any,
    threshold_default: Optional[float],
    *,
    default_source: str,
) -> Dict[str, Any] | None:
    entry = raw_entry if isinstance(raw_entry, Mapping) else {}
    value = _safe_float(entry.get("value")) if entry else None
    if value is None and entry:
        value = _safe_float(entry.get("max_profit") or entry.get("total_profit"))

    threshold = _safe_float(entry.get("threshold")) if entry else None
    if threshold is None and threshold_default is not None:
        threshold = _safe_float(threshold_default)

    if value is None:
        return None

    breach: Optional[bool]
    if threshold is not None:
        breach = value >= threshold
    elif entry and "breach" in entry:
        breach = bool(entry.get("breach"))
    else:
        breach = None

    payload: Dict[str, Any] = {"value": value}
    if threshold is not None:
        payload["threshold"] = threshold
    payload["breach"] = bool(breach) if breach is not None else False

    source = entry.get("source") if entry and isinstance(entry.get("source"), str) else None
    if not source and threshold is not None:
        source = default_source
    if source:
        payload["source"] = source

    return payload


def _build_liquid_snapshot(liquid_entries: Any) -> Dict[str, Dict[str, Any]]:
    payload: Dict[str, Dict[str, Any]] = {}
    thresholds = {str(k).upper(): _safe_float(v) for k, v in LIQ_THR.items()}

    if not isinstance(liquid_entries, list):
        return payload

    for item in liquid_entries:
        if not isinstance(item, Mapping):
            continue

        asset = str(item.get("asset") or item.get("symbol") or "").strip().upper()
        if not asset:
            continue

        value = _safe_float(item.get("value"))
        if value is None:
            value = _safe_float(item.get("dist_pct"))
        if value is None:
            value = _safe_float(item.get("distance"))
        if value is None:
            continue

        threshold = _safe_float(item.get("threshold"))
        if threshold is None:
            threshold = thresholds.get(asset)

        breach: Optional[bool]
        if threshold is not None:
            breach = value > threshold
        elif "breach" in item:
            breach = bool(item.get("breach"))
        else:
            breach = None

        entry_payload: Dict[str, Any] = {"value": value}
        if threshold is not None:
            entry_payload["threshold"] = threshold
        entry_payload["breach"] = bool(breach) if breach is not None else False

        source = item.get("source") if isinstance(item.get("source"), str) else None
        if not source and threshold is not None:
            source = "JSON" if asset in thresholds else "—"
        if source:
            entry_payload["source"] = source

        payload[asset] = entry_payload

    return payload


def _build_profit_snapshot() -> Dict[str, Dict[str, Any]]:
    payload: Dict[str, Dict[str, Any]] = {}
    profit_state = _ALERTS_STATE.get("profit")
    if not isinstance(profit_state, Mapping):
        return payload

    pos_entry = _normalize_profit_entry(
        profit_state.get("position") or profit_state.get("single"),
        _safe_float(PROFIT_POS),
        default_source="JSON",
    )
    if pos_entry:
        payload["single"] = pos_entry

    pf_entry = _normalize_profit_entry(
        profit_state.get("portfolio"),
        _safe_float(PROFIT_PF),
        default_source="JSON",
    )
    if pf_entry:
        payload["portfolio"] = pf_entry

    return payload


def _assemble_monitors_snapshot(target: Dict[str, Any], *, timestamp_iso: Optional[str] = None) -> None:
    ts = timestamp_iso or datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    if ts.endswith("+00:00"):
        ts = ts[:-6] + "Z"

    target["as_of"] = ts

    monitors_payload: Dict[str, Any] = {
        "version": 1,
        "as_of": ts,
        "liquid": {},
        "profit": {},
    }

    liquid_snapshot = _build_liquid_snapshot(_ALERTS_STATE.get("liquid"))
    if liquid_snapshot:
        monitors_payload["liquid"] = liquid_snapshot

    profit_snapshot = _build_profit_snapshot()
    if profit_snapshot:
        monitors_payload["profit"] = profit_snapshot

    target.setdefault("monitors", {})
    target["monitors"] = monitors_payload

# ── legacy thresholds (kept for compatibility with endcap formatting) ────────
def _coerce_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        if isinstance(parsed, Mapping):
            return dict(parsed)
    return {}

def _read_monitor_threshold_sources_legacy(dl: DataLocker) -> tuple[Dict[str, Any], str]:
    values: Dict[str, Any] = {}
    labels: list[str] = []

    system_mgr = getattr(dl, "system", None)
    if system_mgr is not None:
        system_values: Dict[str, Any] = {}
        for key in ("liquid_monitor", "market_monitor", "profit_monitor"):
            try:
                raw = system_mgr.get_var(key)
            except Exception:
                raw = None
            data = _coerce_mapping(raw)
            if data:
                system_values[key] = data
        if system_values:
            values.update(system_values)
            labels.append("DL.system")

    if not values:
        system_vars = getattr(dl, "system_vars", None)
        if isinstance(system_vars, Mapping):
            var_values: Dict[str, Any] = {}
            for key in ("liquid_monitor", "market_monitor", "profit_monitor"):
                data = _coerce_mapping(system_vars.get(key))  # type: ignore[arg-type]
                if data:
                    var_values[key] = data
            if var_values:
                values.update(var_values)
                labels.append("system_vars")

    label = " + ".join(labels)
    return values, label

def _read_monitor_threshold_sources(dl: DataLocker) -> tuple[Dict[str, Any], str]:
    """Return effective monitor thresholds and a summary label for their source.
    JSON-aware: prefers monitor objects (profit_monitor, liquid_monitor) from global_config (FILE)
    and falls back to DL.system_vars (DB)."""

    sysvars = getattr(dl, "system", None)
    gconf   = getattr(dl, "global_config", None)

    sources_used: set[str] = set()

    def _as_dict(val: Any) -> Dict[str, Any]:
        if isinstance(val, Mapping):
            return dict(val)
        if isinstance(val, str):
            try:
                parsed = json.loads(val)
                return dict(parsed) if isinstance(parsed, Mapping) else {}
            except Exception:
                return {}
        return {}

    def _from_gconf(key: str) -> Dict[str, Any]:
        try:
            if isinstance(gconf, Mapping):
                return _as_dict(gconf.get(key))
            if gconf is not None and hasattr(gconf, "get"):
                return _as_dict(gconf.get(key))
        except Exception:
            return {}
        return {}

    def _from_sysvars(key: str) -> Dict[str, Any]:
        try:
            return _as_dict(sysvars.get_var(key)) if sysvars else {}
        except Exception:
            return {}

    profit_obj = _from_gconf("profit_monitor")
    profit_src = "global_config" if profit_obj else ""
    if not profit_obj:
        fallback = _from_sysvars("profit_monitor")
        if fallback:
            profit_obj = fallback
            profit_src = "DL.system_vars"

    liquid_obj = _from_gconf("liquid_monitor")
    liquid_src = "global_config" if liquid_obj else ""
    if not liquid_obj:
        fallback = _from_sysvars("liquid_monitor")
        if fallback:
            liquid_obj = fallback
            liquid_src = "DL.system_vars"

    market_obj = _from_gconf("market_monitor")
    market_src = "global_config" if market_obj else ""
    if not market_obj:
        fallback = _from_sysvars("market_monitor")
        if fallback:
            market_obj = fallback
            market_src = "DL.system_vars"

    profit: Dict[str, Any] = {}
    if profit_obj:
        if "position_profit_usd" in profit_obj:
            profit["pos"] = profit_obj.get("position_profit_usd")
        if "portfolio_profit_usd" in profit_obj:
            profit["pf"] = profit_obj.get("portfolio_profit_usd")
        if profit:
            sources_used.add(profit_src)

    liquid: Dict[str, Any] = {}
    if liquid_obj:
        thresholds = liquid_obj.get("thresholds") if isinstance(liquid_obj, Mapping) else None
        if isinstance(thresholds, Mapping) and thresholds:
            for sym in ("BTC", "ETH", "SOL"):
                if sym in thresholds:
                    liquid[sym.lower()] = thresholds.get(sym)
        else:
            glob = liquid_obj.get("threshold_percent")
            if glob is not None:
                for sym in ("btc", "eth", "sol"):
                    liquid[sym] = glob
        if liquid:
            sources_used.add(liquid_src)

    market: Dict[str, Any] = market_obj if isinstance(market_obj, dict) else {}
    if market:
        sources_used.add(market_src)

    if not (profit or liquid or market):
        return _read_monitor_threshold_sources_legacy(dl)

    sources_used.discard("")
    if not sources_used:
        label = ""
    elif len(sources_used) == 1:
        label = next(iter(sources_used))
    else:
        label = "mixed: " + " + ".join(sorted(sources_used))

    return {"profit": profit, "liquid": liquid, "market": market}, label

def _xcom_live() -> bool:
    """JSON-only control for XCom live/dry-run."""
    return bool(get_xcom_live())

def _format_monitor_lines(status: Optional[MonitorStatus]) -> tuple[str, str]:
    if status is None:
        return "↑0/0/0", "–"

    pos_tokens: list[str] = []
    brief_tokens: list[str] = []
    for monitor_type, detail in status.monitors.items():
        label = {
            MonitorType.SONIC: "Sonic",
            MonitorType.PRICE: "Price",
            MonitorType.POSITIONS: "Positions",
            MonitorType.XCOM: "XCom",
        }.get(monitor_type, monitor_type.value)
        state = getattr(detail.status, "value", str(detail.status))
        meta = detail.metadata if isinstance(getattr(detail, "metadata", None), dict) else {}
        skipped = bool(meta.get("skipped"))
        reason = str(meta.get("reason")) if meta.get("reason") else None
        token = "⏭" if skipped else state
        pos_tokens.append(f"{label}:{token}")
        last_dt = getattr(detail, "last_updated", None)
        last = last_dt.isoformat() if last_dt else "Never"
        if skipped and reason:
            brief_tokens.append(f"{label} → {token} ({reason}; {last})")
        elif skipped:
            brief_tokens.append(f"{label} → {token} ({last})")
        else:
            brief_tokens.append(f"{label} → {state} ({last})")

    pos_line = " • ".join(pos_tokens) if pos_tokens else "↑0/0/0"
    brief = " | ".join(brief_tokens) if brief_tokens else "–"
    return pos_line, brief

def _build_cycle_summary(
    cycle_num: int,
    elapsed: float,
    status: Optional[MonitorStatus],
    *,
    alerts_line: str,
    notifications: Optional[str] = None,
) -> Dict[str, Any]:
    mon_line, mon_brief = _format_monitor_lines(status)
    notif = notifications or (status.sonic_last_complete if status else None)
    if notif:
        notif_line = f"Last sonic completion @ {notif}"
    else:
        notif_line = "NONE (no_breach)"

    summary = {
        "cycle_num": cycle_num,
        "elapsed_s": elapsed,
        "alerts_inline": alerts_line,
        "notifications_brief": notif_line,
        "hedge_groups": 0,
        "monitor_states_line": mon_line,
        "monitor_brief": mon_brief,
    }
    return summary

set_console_title("🦔 Sonic Monitor 🦔")

# neuter legacy console logger unless explicitly enabled
if _os.getenv("SONIC_CONSOLE_LOGGER", "").strip().lower() not in {"1", "true", "on", "yes"}:
    _CONSOLE_REPORT = neuter_legacy_console_logger()
else:
    _CONSOLE_REPORT = {"present": False, "patched": [], "skipped": "ConsoleLogger enabled"}

def _to_iso(ts: Any) -> Optional[str]:
    if ts in (None, "", 0):
        return None
    try:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(float(ts), timezone.utc).isoformat()
        if isinstance(ts, str):
            try:
                return datetime.fromtimestamp(float(ts), timezone.utc).isoformat()
            except ValueError:
                datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return ts
    except Exception:
        return None
    return None

def _fmt_now_clock() -> str:
    # local time of day like "6:23pm"
    s = datetime.now().strftime("%I:%M%p")
    return s.lstrip("0").lower()


def _run_price_and_positions_parallel(cyclone: "Cyclone", logger: Optional[ActivityLogger] = None) -> tuple[dict[str, Any], dict[str, Exception]]:
    def fetch_prices() -> Any:
        if logger is not None:
            with logger.step("Starting Price Sync", icon="🚀", meta={"source": "Cyclone"}):
                return _step("price_sync", cyclone.price_sync.run_full_price_sync, source="Cyclone")
        return _step("price_sync", cyclone.price_sync.run_full_price_sync, source="Cyclone")

    def fetch_positions() -> Any:
        if logger is not None:
            with logger.step("Fetching positions from Jupiter perps-api", icon="🔵", meta={"source": "Cyclone"}):
                return _step(
                    "perps_fetch",
                    cyclone.position_core.update_positions_from_jupiter,
                    "Cyclone",
                )
        return _step(
            "perps_fetch",
            cyclone.position_core.update_positions_from_jupiter,
            "Cyclone",
        )

    t0 = time.perf_counter()
    results: dict[str, Any] = {}
    errors: dict[str, Exception] = {}

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_map = {
            executor.submit(fetch_prices): "price_sync",
            executor.submit(fetch_positions): "perps_fetch",
        }
        for future in as_completed(future_map):
            label = future_map[future]
            try:
                results[label] = future.result()
            except Exception as exc:  # pragma: no cover - defensive guard
                errors[label] = exc
                logging.exception("Parallel step %s failed", label)
                print(f"[PERF] {label} failed: {exc}")
            finally:
                print(f"[PERF] {label} done at {time.perf_counter() - t0:.2f}s")

    print(f"[PERF] parallel total {time.perf_counter() - t0:.2f}s")
    return results, errors

def _enrich_summary_from_locker(summary: Dict[str, Any], dl: DataLocker) -> None:
    # prices (top3) + positions/hedges glance
    try:
        prices = dl.prices.get_all_prices() if getattr(dl, "prices", None) else []
    except Exception:
        prices = []

    top_assets: list[str] = []
    prices_top3: list[tuple[str, float]] = []
    price_changes: Dict[str, bool] = {}
    price_ages: Dict[str, int] = {}
    latest_price_ts: Optional[str] = None

    if prices:
        seen = set()
        sorted_prices = sorted(prices, key=lambda row: float(row.get("last_update_time") or 0.0), reverse=True)
        now_ts = datetime.now(timezone.utc).timestamp()
        for row in sorted_prices:
            asset = str(row.get("asset_type") or "").strip().upper() or "UNKNOWN"
            if asset in seen:
                continue
            seen.add(asset)
            price = float(row.get("current_price") or 0.0)
            prices_top3.append((asset, price))
            top_assets.append(asset)

            last_ts = row.get("last_update_time")
            if latest_price_ts is None:
                latest_price_ts = _to_iso(last_ts)
            try:
                last_float = float(last_ts)
                price_ages[asset] = max(int((now_ts - last_float) // 60), 0)
            except Exception:
                pass

            if len(prices_top3) >= 3:
                break

    if prices_top3:
        summary["prices_top3"] = prices_top3
        summary["assets_line"] = " ".join(top_assets)
    if price_changes:
        summary["price_changes"] = price_changes
    if price_ages:
        summary["price_ages"] = price_ages
    if latest_price_ts:
        summary["prices_updated_at"] = latest_price_ts

    try:
        hedge_mgr = getattr(dl, "hedges", None)
        if hedge_mgr:
            hedges = hedge_mgr.get_hedges() or []
            summary["hedge_groups"] = len(hedges)
    except Exception:
        pass

    try:
        positions = dl.positions.get_all_positions() if getattr(dl, "positions", None) else []
    except Exception:
        positions = []

    if positions:
        active = [p for p in positions if getattr(p, "status", "ACTIVE") != "CLOSED"]
        summary["positions_line"] = f"active {len(active)}/{len(positions)} total"

        def _fmt_position(p: Any) -> str:
            side = getattr(p, "position_type", "").upper() or "–"
            asset = getattr(p, "asset_type", "–")
            size = getattr(p, "size", 0)
            try:
                size_str = f"{float(size):.2f}" if isinstance(size, (int, float)) else str(size)
            except Exception:
                size_str = str(size)
            entry = getattr(p, "entry_price", 0)
            try:
                entry_str = f"{float(entry):.2f}" if isinstance(entry, (int, float)) else str(entry)
            except Exception:
                entry_str = str(entry)
            return f"{asset} {side} {size_str}@{entry_str}"

        try:
            top_positions = sorted(positions, key=lambda p: getattr(p, "last_updated", ""), reverse=True)[:3]
        except Exception:
            top_positions = positions[:3]
        summary["positions_brief"] = " | ".join(_fmt_position(p) for p in top_positions)

        latest_ts: Optional[str] = None
        for pos in positions:
            ts = getattr(pos, "last_updated", None)
            iso = _to_iso(ts)
            if iso:
                if latest_ts is None or iso > latest_ts:
                    latest_ts = iso
        if latest_ts:
            summary["positions_updated_at"] = latest_ts

# ── per-monitor runner wrapper ────────────────────────────────────────────────
async def _run_monitor_tick(name: str, runner: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    key = f"mon_{name}"
    task_start(key, name)
    try:
        result = await asyncio.to_thread(runner, *args, **kwargs)
    except Exception as exc:
        task_end(key, "fail", note=str(exc))
        _MON_STATE[name] = "FAIL"
        if name == "price_monitor":
            set_prices_reason("error")
        if name == "position_monitor":
            set_positions_icon_line(line=None, updated_iso=None, reason="error")
        raise
    else:
        if isinstance(result, dict) and result.get("skipped"):
            task_end(key, "skip", note="fresh")
            _MON_STATE[name] = "⏭"
            if name == "price_monitor":
                set_prices_reason("skipped")
            if name == "position_monitor":
                set_positions_icon_line(line=None, updated_iso=None, reason="skipped")
        else:
            task_end(key, "ok")
            _MON_STATE[name] = "OK"
            if name == "price_monitor":
                set_prices_reason("fresh")
            if name == "position_monitor":
                set_positions_icon_line(line=None, updated_iso=None, reason="fresh")
        if isinstance(result, Mapping):
            _ingest_alert_result(name, result)
        return result

# ── loop interval (JSON-only) ────────────────────────────────────────────────
def get_monitor_interval(db_path: str | None = None, monitor_name: str | None = None) -> int:
    # ignore DB/env; JSON is the source
    return int(LOOP_SECONDS)

# ── heartbeat / ledger (kept as-is) ──────────────────────────────────────────
def update_heartbeat(monitor_name: str, interval_seconds: float, db_path: str | None = None) -> None:
    db_path = db_path or MOTHER_DB_PATH
    dl = DataLocker(str(db_path))
    cursor = dl.db.get_cursor()
    if not cursor:
        logging.error("No DB cursor available; heartbeat not recorded")
        return

    timestamp = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        """
        INSERT INTO monitor_heartbeat (monitor_name, last_run, interval_seconds)
        VALUES (?, ?, ?)
        ON CONFLICT(monitor_name) DO UPDATE
            SET last_run = excluded.last_run,
                interval_seconds = excluded.interval_seconds
        """,
        (monitor_name, timestamp, interval_seconds),
    )
    dl.db.commit()

def write_ledger(status: str, metadata: dict | None = None, db_path: str | None = None) -> None:
    db_path = db_path or MOTHER_DB_PATH
    dl = DataLocker(str(db_path))
    try:
        dl.ledger.insert_ledger_entry(MONITOR_NAME, status=status, metadata=metadata)
    except Exception as exc:
        logging.error(f"Failed to write ledger entry: {exc}")

def heartbeat(loop_counter: int):
    timestamp = datetime.now(timezone.utc).isoformat()
    logging.info("❤️ SonicMonitor heartbeat #%d at %s", loop_counter, timestamp)

# ── main sonic cycle orchestration ───────────────────────────────────────────
from backend.core.monitor_core.monitor_core import MonitorCore

async def sonic_cycle(loop_counter: int, cyclone: Cyclone, logger: Optional[ActivityLogger] = None):
    logging.info("🔄 SonicMonitor cycle #%d starting", loop_counter)

    dl = DataLocker.get_instance(str(MOTHER_DB_PATH))
    cfg = dl.system.get_var("sonic_monitor") or {}

    def _monitor_enabled(cfg_map: Mapping[str, Any], name: str, *, default: bool = True) -> bool:
        override = _ENABLED_OVERRIDES.get(name)
        if override is not None:
            return override
        key = f"enabled_{name}"
        value = cfg_map.get(key, default)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(default if value is None else value)

    sonic_enabled  = _monitor_enabled(cfg, "sonic")
    market_enabled = _monitor_enabled(cfg, "market")
    price_enabled  = _monitor_enabled(cfg, "price",  default=market_enabled)
    profit_enabled = _monitor_enabled(cfg, "profit")
    liquid_enabled = _monitor_enabled(cfg, "liquid")

    _MON_STATE.clear()
    _ALERTS_STATE.clear()

    async def _run_monitor_with_logger(mon_name: str, label: str, icon: str) -> None:
        runner = cyclone.monitor_core.run_by_name
        if logger is not None:
            with logger.step(label, icon=icon, meta={"monitor": mon_name}):
                await _run_monitor_tick(mon_name, runner, mon_name)
        else:
            await _run_monitor_tick(mon_name, runner, mon_name)

    if not sonic_enabled:
        logging.info("Sonic loop disabled via config")
        heartbeat(loop_counter)
        return

    # Fetch prices + Jupiter positions in parallel (ThreadPool to overlap I/O)
    results, errors = await asyncio.to_thread(_run_price_and_positions_parallel, cyclone, logger)

    price_result = results.get("price_sync")
    if price_result is None and "price_sync" in errors:
        logging.error("Price sync step failed: %s", errors["price_sync"])
    elif isinstance(price_result, Mapping):
        if price_result.get("success"):
            logging.info("📈 Prices updated successfully (SonicMonitor)")
            try:
                cyclone._mark_price_monitor_synced()
            except Exception:
                logging.debug("Unable to flag price monitor as synced", exc_info=True)
        elif price_result.get("fallback"):
            logging.warning("Price sync fallback to cached values")
        else:
            err_msg = price_result.get("error") or f"{price_result.get('fetched_count', 0)} assets"
            logging.warning("Price sync reported issues: %s", err_msg)

    positions_result = results.get("perps_fetch")
    if positions_result is None and "perps_fetch" in errors:
        logging.error("Perps fetch step failed: %s", errors["perps_fetch"])
    elif isinstance(positions_result, Mapping):
        fallback_used = bool(positions_result.get("fallback"))
        errors_count = int(positions_result.get("errors", 0) or 0)
        if fallback_used:
            logging.warning("Perps fetch fallback to cached snapshot")
        elif errors_count:
            logging.warning("Perps fetch completed with %d error(s)", errors_count)
        else:
            logging.info("🪐 Position updates completed (SonicMonitor)")
            try:
                cyclone._mark_position_monitor_synced()
            except Exception:
                logging.debug("Unable to flag position monitor as synced", exc_info=True)

    # Run remaining Cyclone steps sequentially
    if logger is not None:
        with logger.step("Run Cyclone processors", icon="🧮", meta={"steps": list(REMAINING_CYCLONE_STEPS)}):
            await cyclone.run_cycle(steps=REMAINING_CYCLONE_STEPS)
    else:
        await cyclone.run_cycle(steps=REMAINING_CYCLONE_STEPS)

    # Run monitors (each will call XCom inline if needed)
    if price_enabled:
        await _run_monitor_with_logger("price_monitor", "Run price monitor", "📈")
    if market_enabled:
        await _run_monitor_with_logger("market_monitor", "Run market monitor", "📊")
    if profit_enabled:
        await _run_monitor_with_logger("profit_monitor", "Run profit monitor", "💰")
    if liquid_enabled:
        await _run_monitor_with_logger("liquid_monitor", "Run liquid monitor", "💧")

    heartbeat(loop_counter)
    logging.info("✅ SonicMonitor cycle #%d complete", loop_counter)
    if logger is not None:
        with logger.step("Notify Sonic listeners", icon="📣"):
            await notify_listeners()
    else:
        await notify_listeners()

def run_monitor(
    dl: Optional[DataLocker] = None,
    poll_interval_s: Optional[int] = None,
    cycles: Optional[int] = None,
) -> None:
    install_compact_console_filter(enable_color=True)
    install_strict_console_filter()
    silence_legacy_console_loggers()

    if dl is None:
        dl = None
        try:
            dl = get_locker()
        except Exception:
            pass
        if dl is None and DL:
            _db = str(MOTHER_DB_PATH) if 'MOTHER_DB_PATH' in globals() else "mother.db"
            try:
                dl = DL.get_instance(_db)
            except Exception:
                dl = DL(_db)
    if DL and dl is not None:
        setattr(DL, "_instance", dl)

    global _ALERT_LIMITS
    try:
        # build thresholds object for alert formatter
        _ALERT_LIMITS = {
            "liquid_monitor": {"thresholds": dict(LIQ_THR)},
            "profit_monitor": {"position_usd": PROFIT_POS, "portfolio_usd": PROFIT_PF},
        }
    except Exception:
        _ALERT_LIMITS = {}

    # JSON-ONLY interval for banner and runtime
    poll_interval_s = int(LOOP_SECONDS)
    try:
        env_loop = _os.getenv("SONIC_MONITOR_LOOP_SECONDS")
        if env_loop and int(float(env_loop)) != poll_interval_s:
            print(f"DEBUG[CFG] ENV loop={env_loop} ignored (JSON ONLY)")
        if getattr(dal, 'system', None):
            db_loop = dal.system.get_var('sonic_monitor_loop_time')
            if db_loop and int(float(db_loop)) != poll_interval_s:
                print(f"DEBUG[CFG] DB loop={db_loop} overwritten by JSON ({poll_interval_s})")
    except Exception:
        pass
    render_startup_banner(dl, DEFAULT_JSON_PATH)
    print(f"DEBUG[XCOM] live={get_xcom_live()} (FILE)")

    monitor_core = MonitorCore()
    cyclone = Cyclone(monitor_core=monitor_core)

    # heartbeat table
    cursor = dl.db.get_cursor()
    if cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS monitor_heartbeat (
                monitor_name TEXT PRIMARY KEY,
                last_run TIMESTAMP NOT NULL,
                interval_seconds INTEGER NOT NULL
            )
            """
        )
        dl.db.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop_counter = 0
    cycle_limit = cycles if cycles is not None and cycles > 0 else None
    print(f"DEBUG[CYCLES] cycle_limit={cycle_limit}  (None means infinite)")

    try:
        while cycle_limit is None or loop_counter < cycle_limit:
            interval = get_monitor_interval()
            if interval <= 0:
                interval = poll_interval_s or DEFAULT_INTERVAL

            # left-aligned cycle header: "✅ cycle #N - <time>"
            loop_counter += 1
            print(f"✅ cycle #{loop_counter} - {_fmt_now_clock()}")
            print()  # one blank line before first step

            start_time = time.time()
            cycle_failed = False
            logger = ActivityLogger()
            logger.begin_cycle(loop_counter)

            try:
                with logger.step("Run sonic cycle", icon="🦔"):
                    loop.run_until_complete(sonic_cycle(loop_counter, cyclone, logger=logger))
                with logger.step("Update heartbeat", icon="❤️"):
                    update_heartbeat(MONITOR_NAME, interval)
                with logger.step("Write success ledger entry", icon="📘"):
                    write_ledger("Success")
            except Exception as exc:
                cycle_failed = True
                logging.exception("SonicMonitor cycle failure")
                with logger.step("Write error ledger entry", icon="📘"):
                    write_ledger("Error", {"error": str(exc)})

            # build & print summary
            status_snapshot: Optional[MonitorStatus] = None
            try:
                status_snapshot = dl.ledger.get_monitor_status_summary()
                payload = (status_snapshot.model_dump() if hasattr(status_snapshot, "model_dump")
                           else (status_snapshot.dict() if hasattr(status_snapshot, "dict")
                                 else status_snapshot))
                logging.debug("Monitor status summary: %s", payload)
            except Exception:
                logging.exception("Failed to update monitor status summary")

            elapsed = time.time() - start_time
            alerts_line = "fail 1/1 error" if cycle_failed else "pass 0/0 –"

            icon_line: Optional[str] = None
            try:
                db_obj = getattr(dl, "db", None)
                conn = getattr(db_obj, "conn", None) if db_obj is not None else None
                icon_line = compute_positions_icon_line(conn if conn is not None else None)
            except Exception:
                logging.debug("positions icon line computation failed", exc_info=True)

            if not icon_line:
                try:
                    icon_line = compute_from_list(getattr(dl, "last_positions_fetch", None))
                except Exception:
                    icon_line = None

            summary = _build_cycle_summary(loop_counter, elapsed, status_snapshot, alerts_line=alerts_line)
            if icon_line:
                summary["positions_icon_line"] = icon_line

            # populate prices/positions/hedges into summary for endcap
            with (logger.step("Summarize prices", icon="💹", meta={"source": "DataLocker"}) if logger else nullcontext()):
                try:
                    price_mgr = getattr(dl, "prices", None)
                    if price_mgr:
                        price_rows = price_mgr.get_all_prices() or []
                        top3: list[tuple[str, float]] = []
                        price_ages: dict[str, int] = {}
                        seen_assets: set[str] = set()
                        latest_iso: Optional[str] = None
                        now_ts = datetime.now(timezone.utc).timestamp()
                        for row in price_rows:
                            asset = str(row.get("asset_type") or "").upper() or "UNKNOWN"
                            if asset in seen_assets:
                                continue
                            seen_assets.add(asset)
                            try:
                                price_val = float(row.get("current_price") or 0.0)
                            except Exception:
                                price_val = 0.0
                            top3.append((asset, price_val))
                            last_ts = row.get("last_update_time")
                            iso = _to_iso(last_ts)
                            if iso and (latest_iso is None or iso > latest_iso):
                                latest_iso = iso
                            try:
                                last_float = float(last_ts)
                                price_ages[asset] = max(int((now_ts - last_float) // 60), 0)
                            except Exception:
                                pass
                            if len(top3) >= 3:
                                break
                        if not top3:
                            desired = get_price_assets()
                            top3 = [(asset, float("nan")) for asset in desired]
                        if top3:
                            summary["prices_top3"] = top3
                        if price_ages:
                            summary["price_ages"] = price_ages
                        if latest_iso and not summary.get("prices_updated_at"):
                            summary["prices_updated_at"] = latest_iso
                        set_prices(top3, latest_iso)
                except Exception:
                    logging.debug("Failed to populate price summary", exc_info=True)
                    set_prices([], None)
                    set_prices_reason("error")

            with (logger.step("Snapshot portfolio", icon="💾", meta={"source": "collect_positions"}) if logger else nullcontext()):
                try:
                    pos_rows, pos_error, pos_meta = collect_positions(dl)
                    summary["positions_error"] = pos_error
                    summary["positions_count"] = len(pos_rows)
                    summary["positions_provider"] = pos_meta.get("provider") if pos_meta else None
                    summary["positions_source"] = pos_meta.get("source") if pos_meta else None
                    latest_iso: Optional[str] = None
                    positions_block: Optional[Dict[str, Any]] = None
                    if pos_meta.get("provider") or pos_meta.get("source") or pos_rows:
                        positions_block = summary.setdefault("positions", {})
                        if pos_meta.get("provider"):
                            positions_block["provider"] = pos_meta["provider"]
                        if pos_meta.get("source"):
                            positions_block["source"] = pos_meta["source"]
                    if pos_rows:
                        if positions_block is None:
                            positions_block = summary.setdefault("positions", {})
                        positions_block["rows"] = pos_rows
                        try:
                            setattr(dl, "last_positions_fetch", pos_rows)
                        except Exception:
                            pass
                        for pos in pos_rows:
                            iso = _to_iso(pos.get("ts") or pos.get("last_updated"))
                            if iso and (latest_iso is None or iso > latest_iso):
                                latest_iso = iso
                    else:
                        positions_mgr = getattr(dl, "positions", None)
                        if positions_mgr:
                            try:
                                fallback_rows = positions_mgr.get_all_positions() or []
                            except Exception:
                                fallback_rows = []
                            for pos in fallback_rows:
                                iso = _to_iso(getattr(pos, "last_updated", None))
                                if iso and (latest_iso is None or iso > latest_iso):
                                    latest_iso = iso
                    if latest_iso and not summary.get("positions_updated_at"):
                        summary["positions_updated_at"] = latest_iso
                    if pos_error:
                        summary["positions_error"] = pos_error
                    set_positions_icon_line(
                        line=icon_line if icon_line else None,
                        updated_iso=summary.get("positions_updated_at") or latest_iso,
                        reason=None,
                    )
                except Exception:
                    logging.debug("Failed to populate position summary", exc_info=True)
                    summary.setdefault("positions_error", "positions summary failure")
                    set_positions_icon_line(line=None, updated_iso=None, reason="error")

            with (logger.step("Update hedge snapshot", icon="🛡", meta={"source": "hedges"}) if logger else nullcontext()):
                try:
                    hedge_mgr = getattr(dl, "hedges", None)
                    if hedge_mgr:
                        hedges = hedge_mgr.get_hedges() or []
                        summary["hedge_groups"] = len(hedges)
                        set_hedges(len(hedges))
                        try:
                            setattr(dl, "last_hedge_groups", int(len(hedges)))
                        except Exception:
                            pass
                except Exception:
                    logging.debug("Failed to populate hedge summary", exc_info=True)
                    fallback_hedges = getattr(dl, "last_hedge_groups", None)
                    if fallback_hedges is not None and "hedge_groups" not in summary:
                        summary["hedge_groups"] = int(fallback_hedges)
                        set_hedges(int(fallback_hedges))

            # rebuild/count hedges from DB (if supported)
            with (logger.step("Rebuild hedge groups", icon="🧩", meta={"source": "DLHedgeManager"}) if logger else nullcontext()):
                try:
                    if getattr(dal, "db", None):
                        hmgr = DLHedgeManager(dal.db)
                        for fn in ("rebuild_groups_from_positions", "rebuild_from_positions", "rebuild", "refresh"):
                            if hasattr(hmgr, fn):
                                try:
                                    getattr(hmgr, fn)()
                                    break
                                except Exception:
                                    pass
                        hedge_count = 0
                        if hasattr(hmgr, "count_groups"):
                            try:
                                hedge_count = int(hmgr.count_groups() or 0)
                            except Exception:
                                hedge_count = 0
                        summary["hedge_groups"] = hedge_count
                        set_hedges(hedge_count)
                        try:
                            setattr(dl, "last_hedge_groups", int(hedge_count))
                        except Exception:
                            pass
                except Exception:
                    pass

            # monitors strip & alerts
            try:
                if _MON_STATE:
                    ordered_keys = ("price_monitor","market_monitor","profit_monitor","liquid_monitor","position_monitor")
                    tokens: list[str] = []
                    for key in ordered_keys:
                        if key in _MON_STATE:
                            tokens.append(f"{key.replace('_monitor','')}:{_MON_STATE[key]}")
                    if tokens:
                        # keep monitor health on its own line
                        summary["monitors_inline"] = " ".join(tokens)
                        # if alerts line is empty, use monitors as a fallback
                        summary.setdefault("alerts_inline", summary["monitors_inline"])
            except Exception:
                pass

            if not cycle_failed:
                details = compose_alerts_inline(_ALERTS_STATE)
                summary["alerts_inline"] = details if details and details != "none" else summary.get("monitors_inline", "none")
            else:
                summary["alerts_inline"] = "fail 1/1 error"

            try:
                errors = sum(1 for state in _MON_STATE.values() if str(state).upper() == "FAIL")
                if cycle_failed: errors += 1
                summary["errors_count"] = int(errors)
            except Exception:
                if cycle_failed: summary["errors_count"] = 1

            with (logger.step("Enrich summary from locker", icon="📦") if logger else nullcontext()):
                try:
                    _enrich_summary_from_locker(summary, dl)
                except Exception:
                    logging.exception("Failed to enrich sonic summary")

            if icon_line:
                summary.setdefault("positions_icon_line", icon_line)
                set_positions_icon_line(line=icon_line, updated_iso=summary.get("positions_updated_at"), reason=None)

            cfg_for_endcap = {}
            try:
                cfg_for_endcap = dl.system.get_var("sonic_monitor") or {}
            except Exception:
                logging.debug("Failed to load sonic_monitor config", exc_info=True)

            print()  # breathing room before summary
            summary = snapshot_into(summary)
            cycle_snapshot = summary
            _assemble_monitors_snapshot(cycle_snapshot)
            # ---- Alerts detail + sources snapshot (tolerant; safe when missing) ----
            try:
                cfg_snapshot = load_monitor_config_snapshot(summary)
                summary["sources"] = build_sources_snapshot(cfg_snapshot)
                # build detail only if monitors didn't already include it
                summary.setdefault("alerts", {})
                if not isinstance(summary["alerts"].get("detail"), dict):
                    summary["alerts"]["detail"] = build_alerts_detail(summary, cfg_snapshot)
            except Exception as _e:
                # don't fail the cycle on cosmetics; console will show ✓ for missing detail
                pass
            try:
                cycle_summary = logger.end_cycle()
            except Exception:
                cycle_summary = {"id": loop_counter, "started_at": None, "activities": []}
            if dl is not None:
                try:
                    if hasattr(dl, "set_last_cycle"):
                        dl.set_last_cycle(cycle_summary)
                    else:
                        setattr(dl, "last_cycle", cycle_summary)
                except Exception:
                    logging.debug("Failed to persist cycle activities", exc_info=True)
            # 3) Render modular Sonic reporting UI (sync, evaluations, positions, prices)
            if dl is not None:
                cycle_snapshot["prices"] = _csum_prices(dl)
                cycle_snapshot["pos_rows"] = _csum_positions(dl)
                if DEBUG_DUMP_SNAPSHOT:
                    _dump_cycle_snapshot(cycle_snapshot, title="PRE-RENDER HANDOFF")
                render_cycle(dl, cycle_snapshot, default_json_path=DEFAULT_JSON_PATH)

            # 4) Then emit compact line and JSON summary (derive elapsed/sleep defensively)
            cl.emit_compact_cycle(
                summary,
                cfg_for_endcap,
                interval,
                enable_color=True,
            )
            cyc_ms = int((summary.get("durations", {}) or {}).get("cyclone_ms") or 0)
            elapsed_for_emit = float(summary.get("elapsed_s") or 0.0)
            if elapsed_for_emit <= 0 and cyc_ms > 0:
                elapsed_for_emit = cyc_ms / 1000.0
            if elapsed_for_emit <= 0:
                elapsed_for_emit = float(elapsed)
            sleep_time = max(0.0, float(interval) - float(elapsed_for_emit or 0.0))
            emit_json_summary(
                summary,
                cyc_ms,
                loop_counter,
                elapsed_for_emit,
                sleep_time,
            )
            # ---- Sources line (compact) + optional deep trace ----
            try:
                from backend.core.reporting_core.console_reporter import emit_sources_line
            except Exception:
                def emit_sources_line(sources, label):
                    line = "   🧭 Sources  : " + str(sources) + (f" ← {label}" if label else "")
                    print(line)

            try:
                from backend.core.monitor_core.utils.trace_sources import (
                    read_monitor_threshold_sources,
                    trace_monitor_thresholds,
                    pretty_print_trace,
                )
                if _os.getenv("SONIC_SHOW_SOURCES", "1") != "0":
                    sources, src_label = read_monitor_threshold_sources(dl)
                    emit_sources_line(sources, src_label)
                if _os.getenv("SONIC_TRACE_THRESHOLDS", "0") == "1":
                    pretty_print_trace(trace_monitor_thresholds(dl))
            except Exception as _e:
                print(f"   (trace disabled: {_e})")
            # ------------------------------------------------------

            print()  # spacer between cycles

            # sleep until next cycle based on JSON-only interval
            sleep_time = max(
                0.0,
                float(interval) - float(summary.get("elapsed_s", elapsed_for_emit)),
            )
            if sleep_time > 0:
                spin_progress(
                    sleep_time,
                    style=style_for_cycle(loop_counter),
                    label=f"sleep {int(round(sleep_time))}s",
                    bar_colorizer=lambda bar: f"{_CYAN}{bar}{_RST}",
                )

    except KeyboardInterrupt:
        logging.info("SonicMonitor terminated by user.")
    finally:
        try:
            loop.close()
        except Exception:
            pass


if __name__ == "__main__":
    run_monitor()
