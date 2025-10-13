import json
import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Dict, Optional, Callable

# --- Ensure absolute imports resolve when launching this file directly ---------
if __package__ in (None, ""):
    _REPO_ROOT = Path(__file__).resolve().parents[3]
    _BACKEND_ROOT = _REPO_ROOT / "backend"
    for _p in (str(_REPO_ROOT), str(_BACKEND_ROOT)):
        if _p not in sys.path:
            sys.path.insert(0, _p)


def _resolve_and_load_env() -> str | None:
    """
    Find the intended .env file and load it once.
    Priority:
      1) SONIC_ENV_PATH (explicit override)
      2) repo root /.env
      3) backend/.env
      4) CWD/.env
      5) python-dotenv discovery (find_dotenv)
    Saves the resolved path into SONIC_ENV_PATH_RESOLVED for banner usage.
    """

    try:
        from dotenv import load_dotenv, find_dotenv  # type: ignore
    except Exception:
        return None

    here = Path(__file__).resolve()
    repo_root = here.parents[3] if len(here.parents) >= 4 else Path.cwd()

    candidates: list[Path] = []
    explicit = os.getenv("SONIC_ENV_PATH")
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

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"
for _candidate in (REPO_ROOT, BACKEND_ROOT):
    _candidate_str = str(_candidate)
    if _candidate_str not in sys.path:
        sys.path.insert(0, _candidate_str)

# Build DAL from sonic_config.json (or env) — no shared_store.
from backend.config.config_loader import load_config
from backend.data.data_locker import DataLocker


def _json_path() -> str:
    return os.getenv("SONIC_MONITOR_CONFIG_PATH") or str(
        Path(__file__).resolve().parents[2] / "config" / "sonic_monitor_config.json"
    )


def _expand_env(node):
    if isinstance(node, str):
        m = re.fullmatch(r"\$\{([^}]+)\}", node.strip())
        return os.getenv(m.group(1), node) if m else node
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
        data = load_config(path) or {}
        if not isinstance(data, dict):
            return {}
        return _expand_env(data)
    except Exception as exc:
        print(f"❌ JSON load error ({path}): {exc.__class__.__name__}: {exc}")
        raise SystemExit(2)


CFG: Dict[str, Any] = _load_json_only()

MOTHER_DB_PATH = (
    (CFG.get("system_config") or {}).get("db_path")
    or os.getenv("SONIC_DB_PATH")
    or str(Path(__file__).resolve().parents[2] / "mother.db")
)
MONITOR_NAME = "sonic_monitor"


dal = DataLocker.get_instance(MOTHER_DB_PATH)


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


LOOP_SECONDS = _require(
    "system_config.sonic_loop_delay | monitor.loop_seconds",
    _get(CFG, "system_config", "sonic_loop_delay")
    or _get(CFG, "monitor", "loop_seconds"),
    coerce=lambda x: int(float(x)),
)

LIQ_THR = _require(
    "liquid.thresholds | liquid_monitor.thresholds",
    _get(CFG, "liquid", "thresholds")
    or _get(CFG, "liquid_monitor", "thresholds"),
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

TW = {
    "sid": _get(CFG, "twilio", "sid"),
    "auth": _get(CFG, "twilio", "auth"),
    "from": _get(CFG, "twilio", "from"),
    "to": _get(CFG, "twilio", "to"),
    "flow": _get(CFG, "twilio", "flow"),
}

try:
    sysmgr = dal.system
    sysmgr.set_var("sonic_monitor_loop_time", LOOP_SECONDS)
    sysmgr.set_var(
        "alert_thresholds",
        json.dumps({"thresholds": LIQ_THR, "blast": LIQ_BLAST}, separators=(",", ":")),
    )
    sysmgr.set_var("profit_pos", PROFIT_POS)
    sysmgr.set_var("profit_pf", PROFIT_PF)
    sysmgr.set_var("profit_badge_value", PROFIT_PF)
except Exception as exc:
    print(f"⚠ DB seed from JSON failed: {exc}")


xcom_json = _get(CFG, "monitor", "xcom_live")
if isinstance(xcom_json, bool):
    os.environ["SONIC_XCOM_LIVE"] = "1" if xcom_json else "0"


# Convenience getters (use these instead of config_bridge.get_*)
def cfg_loop_seconds(default: int | None) -> int | None:
    return LOOP_SECONDS if LOOP_SECONDS is not None else default


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


def cfg_twilio() -> dict:
    return dict(TW)


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


try:
    _db_monitor_cfg_raw = (
        dal.system.get_var("sonic_monitor") if getattr(dal, "system", None) else {}
    )
    _db_monitor_cfg = dict(_db_monitor_cfg_raw) if isinstance(_db_monitor_cfg_raw, Mapping) else {}
except Exception:
    _db_monitor_cfg = {}

_loop_from_cfg_raw = cfg_loop_seconds(None)
_LOOP_SECONDS_OVERRIDE: Optional[int]
try:
    loop_val = int(_loop_from_cfg_raw) if _loop_from_cfg_raw is not None else None
    _LOOP_SECONDS_OVERRIDE = loop_val if loop_val and loop_val > 0 else None
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

_ENABLED_OVERRIDES: dict[str, Optional[bool]] = {}
for name, value in _enabled_overrides_raw.items():
    if value is None:
        _ENABLED_OVERRIDES[name] = None
    else:
        _ENABLED_OVERRIDES[name] = bool(value)

_xcom_from_json = cfg_xcom_live(None)
if _xcom_from_json is not None:
    os.environ["SONIC_XCOM_LIVE"] = "1" if _xcom_from_json else "0"

_liq_thr_cfg = cfg_liquid_thresholds()
_blast_cfg = cfg_liquid_blast()
_profit_cfg = cfg_profit_thresholds()


def _monitor_enabled(cfg: Mapping[str, Any], name: str, *, default: bool = True, alias: str | None = None) -> bool:
    """Resolve monitor enable flags with JSON override → DB fallback."""

    override = _ENABLED_OVERRIDES.get(name)
    if override is not None:
        return override

    key = alias or f"enabled_{name}"
    value = cfg.get(key, default)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(default if value is None else value)


import asyncio
import logging
import time
from datetime import datetime, timezone

from backend.core.monitor_core.utils.console_title import set_console_title
from backend.core.cyclone_core.cyclone_engine import Cyclone
from backend.core.monitor_core.utils.banner import emit_config_banner
from backend.core.monitor_core.sonic_events import notify_listeners
from backend.core.reporting_core.task_events import task_start, task_end
from backend.core.reporting_core.console_lines import emit_compact_cycle
from backend.core.reporting_core.positions_icons import compute_positions_icon_line, compute_from_list
from backend.core.reporting_core.console_reporter import (
    install_strict_console_filter,
    neuter_legacy_console_logger,
    silence_legacy_console_loggers,
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
from backend.core.config.json_config import load_config as load_json_config
from backend.models.monitor_status import MonitorStatus, MonitorType
DEFAULT_INTERVAL = 60  # fallback if nothing set in DB

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

_MONITOR_LABELS: Dict[MonitorType, str] = {
    MonitorType.SONIC: "Sonic",
    MonitorType.PRICE: "Price",
    MonitorType.POSITIONS: "Positions",
    MonitorType.XCOM: "XCom",
}


_MON_STATE: Dict[str, str] = {}
_ALERTS_STATE: Dict[str, Any] = {}
_ALERT_LIMITS: Dict[str, Any] = {}


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
    json_values: Dict[str, Any] = {}

    if _liq_thr_cfg or _blast_cfg:
        liq_section: Dict[str, Any] = {}
        if _liq_thr_cfg:
            liq_section["thresholds"] = {}
            for asset, value in _liq_thr_cfg.items():
                try:
                    liq_section["thresholds"][str(asset).upper()] = float(value)
                except Exception:
                    continue
        if _blast_cfg:
            liq_section["blast_radius"] = {}
            for asset, value in _blast_cfg.items():
                try:
                    liq_section["blast_radius"][str(asset).upper()] = float(value)
                except Exception:
                    continue
        if liq_section:
            json_values["liquid_monitor"] = liq_section

    if _profit_cfg:
        profit_section: Dict[str, Any] = {}
        pos = _profit_cfg.get("position_usd") or _profit_cfg.get("position_profit_usd")
        pf = _profit_cfg.get("portfolio_usd") or _profit_cfg.get("portfolio_profit_usd")
        try:
            if pos is not None:
                profit_section["position_profit_usd"] = int(float(pos))
        except Exception:
            pass
        try:
            if pf is not None:
                profit_section["portfolio_profit_usd"] = int(float(pf))
        except Exception:
            pass
        if profit_section:
            json_values["profit_monitor"] = profit_section

    if json_values:
        return json_values, "JSON"

    try:
        json_cfg = load_json_config()
    except Exception:
        json_cfg = {}

    for key in ("liquid_monitor", "market_monitor", "profit_monitor"):
        section = json_cfg.get(key)
        if isinstance(section, Mapping) and section:
            json_values[key] = dict(section)

    if json_values:
        return json_values, "JSON"

    return _read_monitor_threshold_sources_legacy(dl)


def _xcom_live() -> bool:
    return os.getenv("SONIC_XCOM_LIVE", "1").strip().lower() not in {"0", "false", "no", "off"}


def _format_monitor_lines(status: Optional[MonitorStatus]) -> tuple[str, str]:
    if status is None:
        return "↑0/0/0", "–"

    pos_tokens: list[str] = []
    brief_tokens: list[str] = []
    for monitor_type, detail in status.monitors.items():
        label = _MONITOR_LABELS.get(monitor_type, monitor_type.value)
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
    pos_line, brief = _format_monitor_lines(status)
    notif = notifications or (status.sonic_last_complete if status else None)
    if notif:
        notif_line = f"Last sonic completion @ {notif}"
    else:
        notif_line = "NONE (no_breach)"

    summary = {
        "cycle_num": cycle_num,
        "elapsed_s": elapsed,
        "positions_line": pos_line,
        "positions_brief": brief,
        "alerts_inline": alerts_line,
        "notifications_brief": notif_line,
        "hedge_groups": 0,
    }

    summary["monitor_states_line"] = pos_line
    summary["monitor_brief"] = brief
    return summary


set_console_title("🦔 Sonic Monitor 🦔")

if os.getenv("SONIC_CONSOLE_LOGGER", "").strip().lower() not in {"1", "true", "on", "yes"}:
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
                # assume already iso-formatted
                datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return ts
    except Exception:
        return None
    return None


def _enrich_summary_from_locker(summary: Dict[str, Any], dl: DataLocker) -> None:
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
        # Deduplicate by asset_type preserving latest order
        seen = set()
        sorted_prices = sorted(
            prices,
            key=lambda row: float(row.get("last_update_time") or 0.0),
            reverse=True,
        )
        now_ts = datetime.now(timezone.utc).timestamp()
        for row in sorted_prices:
            asset = str(row.get("asset_type") or "").strip() or "UNKNOWN"
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

            prev = row.get("previous_price")
            try:
                price_changes[asset] = float(prev or 0.0) != float(price)
            except Exception:
                price_changes[asset] = False

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

    # Hedge snapshot — count active hedge groups for console endcap
    try:
        hedge_mgr = getattr(dl, "hedges", None)
        if hedge_mgr:
            hedges = hedge_mgr.get_hedges() or []
            summary["hedge_groups"] = len(hedges)
    except Exception:
        pass

    # Positions snapshot
    try:
        positions = (
            dl.positions.get_all_positions() if getattr(dl, "positions", None) else []
        )
    except Exception:
        positions = []

    if positions:
        active = [p for p in positions if getattr(p, "status", "ACTIVE") != "CLOSED"]
        summary["positions_line"] = f"active {len(active)}/{len(positions)} total"

        # top 3 holdings summary
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
            top_positions = sorted(
                positions,
                key=lambda p: getattr(p, "last_updated", ""),
                reverse=True,
            )[:3]
        except Exception:
            top_positions = positions[:3]
        summary["positions_brief"] = " | ".join(_fmt_position(p) for p in top_positions)

        # Determine latest timestamp
        latest_ts: Optional[str] = None
        for pos in positions:
            ts = getattr(pos, "last_updated", None)
            iso = _to_iso(ts)
            if iso:
                if latest_ts is None or iso > latest_ts:
                    latest_ts = iso
        if latest_ts:
            summary["positions_updated_at"] = latest_ts



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

def get_monitor_interval(db_path: str | None = None, monitor_name: str | None = None):
    _ = db_path or MOTHER_DB_PATH
    _ = monitor_name or MONITOR_NAME

    if _LOOP_SECONDS_OVERRIDE is not None and _LOOP_SECONDS_OVERRIDE > 0:
        return int(_LOOP_SECONDS_OVERRIDE)

    return int(LOOP_SECONDS)


def update_heartbeat(
    monitor_name: str,
    interval_seconds: float,
    db_path: str | None = None,
) -> None:
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
    except Exception as exc:  # pragma: no cover - log ledger failures
        logging.error(f"Failed to write ledger entry: {exc}")


def heartbeat(loop_counter: int):
    timestamp = datetime.now(timezone.utc).isoformat()
    logging.info("❤️ SonicMonitor heartbeat #%d at %s", loop_counter, timestamp)


async def sonic_cycle(loop_counter: int, cyclone: Cyclone):
    """Run a full Cyclone cycle and then execute enabled monitors."""
    logging.info("🔄 SonicMonitor cycle #%d starting", loop_counter)

    dl = DataLocker.get_instance()
    cfg = dl.system.get_var("sonic_monitor") or {}

    sonic_enabled = _monitor_enabled(cfg, "sonic")
    market_enabled = _monitor_enabled(cfg, "market")
    price_enabled = _monitor_enabled(cfg, "price", default=market_enabled)
    profit_enabled = _monitor_enabled(cfg, "profit")
    liquid_enabled = _monitor_enabled(cfg, "liquid")

    _MON_STATE.clear()
    _ALERTS_STATE.clear()

    if not sonic_enabled:
        logging.info("Sonic loop disabled via config")
        heartbeat(loop_counter)
        return

    # Execute the complete Cyclone pipeline
    await cyclone.run_cycle()

    # Run monitors based on config
    if price_enabled:
        await _run_monitor_tick("price_monitor", cyclone.monitor_core.run_by_name, "price_monitor")
    else:
        logging.info("Price monitor disabled via configuration")

    if market_enabled:
        await _run_monitor_tick("market_monitor", cyclone.monitor_core.run_by_name, "market_monitor")
    else:
        logging.info("Market monitor disabled via configuration")

    if profit_enabled:
        await _run_monitor_tick("profit_monitor", cyclone.monitor_core.run_by_name, "profit_monitor")
    else:
        logging.info("Profit monitor disabled via configuration")
    # await asyncio.to_thread(cyclone.monitor_core.run_by_name, "risk_monitor")
    if liquid_enabled:
        await _run_monitor_tick("liquid_monitor", cyclone.monitor_core.run_by_name, "liquid_monitor")
    else:
        logging.info("Liquidation monitor disabled via configuration")

    # Alert V2 pipeline disabled

    heartbeat(loop_counter)
    logging.info("✅ SonicMonitor cycle #%d complete", loop_counter)

    await notify_listeners()


def run_monitor(
    dl: Optional[DataLocker] = None,
    poll_interval_s: Optional[int] = None,
    cycles: Optional[int] = None,
) -> None:
    """Run the Sonic monitor console loop."""

    # 0) lock console down…
    install_strict_console_filter()
    muted = silence_legacy_console_loggers()

    from backend.core.monitor_core.monitor_core import MonitorCore

    if dl is None:
        dl = DataLocker.get_instance(str(MOTHER_DB_PATH))
    else:
        # Ensure the provided locker is reused by singleton consumers
        setattr(DataLocker, "_instance", dl)

    global _ALERT_LIMITS
    try:
        _ALERT_LIMITS, _ = _read_monitor_threshold_sources(dl)
    except Exception:
        _ALERT_LIMITS = {}

    poll_interval_s = _LOOP_SECONDS_OVERRIDE or LOOP_SECONDS
    if not poll_interval_s:
        poll_interval_s = DEFAULT_INTERVAL

    display_interval = poll_interval_s or DEFAULT_INTERVAL

    # 1) standard config banner (single unified "Sonic Monitor Configuration" block)
    emit_config_banner(
        dl,
        poll_interval_s,
        muted_modules=muted,
        xcom_live=_xcom_live(),
        config_source=("JSON ONLY", _json_path()),
    )

    monitor_core = MonitorCore()
    cyclone = Cyclone(monitor_core=monitor_core)

    cursor = dl.db.get_cursor()
    if not cursor:
        logging.error("No DB cursor available; cannot initialize heartbeat table")
        return
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
    try:
        while cycle_limit is None or loop_counter < cycle_limit:
            interval = get_monitor_interval()
            if interval <= 0:
                interval = display_interval

            print(f"◆ cycle #{loop_counter + 1} start")
            print()
            loop_counter += 1
            start_time = time.time()
            cycle_failed = False

            try:
                loop.run_until_complete(sonic_cycle(loop_counter, cyclone))
                update_heartbeat(MONITOR_NAME, interval)
                write_ledger("Success")
            except Exception as exc:  # pragma: no cover - runtime safety
                cycle_failed = True
                logging.exception("SonicMonitor cycle failure")
                write_ledger("Error", {"error": str(exc)})

            status_snapshot: Optional[MonitorStatus] = None
            try:
                status_snapshot = dl.ledger.get_monitor_status_summary()
                if hasattr(status_snapshot, "model_dump"):
                    payload = status_snapshot.model_dump()
                elif hasattr(status_snapshot, "dict"):
                    payload = status_snapshot.dict()
                else:
                    payload = status_snapshot
                logging.debug("Monitor status summary: %s", payload)
            except Exception:  # pragma: no cover - defensive logging
                logging.exception("Failed to update monitor status summary")

            elapsed = time.time() - start_time
            alerts_line = "fail 1/1 error" if cycle_failed else "pass 0/0 –"
            icon_line: Optional[str] = None
            try:
                db_manager = getattr(dl, "db", None)
                conn = None
                if db_manager is not None:
                    conn = getattr(db_manager, "conn", None) or db_manager.connect()
                icon_line = compute_positions_icon_line(conn)
            except Exception:
                logging.debug("positions icon line computation failed", exc_info=True)
            if not icon_line:
                try:
                    fallback_positions = getattr(dl, "last_positions_fetch", None)
                    icon_line = compute_from_list(fallback_positions)
                except Exception:
                    icon_line = None
            summary = _build_cycle_summary(
                loop_counter,
                elapsed,
                status_snapshot,
                alerts_line=alerts_line,
            )
            # Populate summary data directly from the DataLocker so the endcap has
            # fresh values even if later enrich steps fail.
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
            try:
                positions_mgr = getattr(dl, "positions", None)
                if positions_mgr:
                    positions = positions_mgr.get_all_positions() or []
                    latest_iso: Optional[str] = None
                    for pos in positions:
                        iso = _to_iso(getattr(pos, "last_updated", None))
                        if iso and (latest_iso is None or iso > latest_iso):
                            latest_iso = iso
                    if latest_iso and not summary.get("positions_updated_at"):
                        summary["positions_updated_at"] = latest_iso
                set_positions_icon_line(
                    line=icon_line if icon_line else None,
                    updated_iso=summary.get("positions_updated_at") or latest_iso,
                    reason=None,
                )
            except Exception:
                logging.debug("Failed to populate position summary", exc_info=True)
                set_positions_icon_line(line=None, updated_iso=None, reason="error")
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
            try:
                if getattr(dal, "db", None):
                    hmgr = DLHedgeManager(dal.db)
                    for fn in (
                        "rebuild_groups_from_positions",
                        "rebuild_from_positions",
                        "rebuild",
                        "refresh",
                    ):
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
                    else:
                        try:
                            cur = dal.db.execute(
                                "SELECT COUNT(DISTINCT group_id) AS n FROM hedges"
                            )
                            row = cur.fetchone()
                            if row is not None:
                                if isinstance(row, Mapping):
                                    hedge_count = int(row.get("n") or 0)
                                else:
                                    hedge_count = int(row[0] if len(row) else 0)
                        except Exception:
                            try:
                                cur = dal.db.execute(
                                    """
                                    SELECT asset,
                                           SUM(CASE WHEN side IN ('long','L',1) THEN 1 ELSE 0 END) AS longs,
                                           SUM(CASE WHEN side IN ('short','S',0) THEN 1 ELSE 0 END) AS shorts
                                      FROM positions
                                     WHERE is_open=1
                                     GROUP BY asset
                                    """
                                )
                                hedge_count = 0
                                for r in cur.fetchall() or []:
                                    if isinstance(r, Mapping):
                                        longs = r.get("longs") or 0
                                        shorts = r.get("shorts") or 0
                                    else:
                                        longs = r[1] if len(r) > 1 else 0
                                        shorts = r[2] if len(r) > 2 else 0
                                    if (longs or 0) > 0 and (shorts or 0) > 0:
                                        hedge_count += 1
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
            if "hedge_groups" not in summary:
                fallback_hedges = getattr(dl, "last_hedge_groups", None)
                if fallback_hedges is not None:
                    summary["hedge_groups"] = int(fallback_hedges)
                    set_hedges(int(fallback_hedges))
            try:
                if _MON_STATE:
                    ordered_keys = (
                        "price_monitor",
                        "market_monitor",
                        "profit_monitor",
                        "liquid_monitor",
                        "position_monitor",
                    )
                    tokens: list[str] = []
                    for key in ordered_keys:
                        if key in _MON_STATE:
                            label = key.replace("_monitor", "")
                            tokens.append(f"{label}:{_MON_STATE[key]}")
                    if tokens:
                            summary["monitors_inline"] = " ".join(tokens)
                            summary["alerts_inline"] = summary.get("alerts_inline") or summary[
                                "monitors_inline"
                            ]
            except Exception:
                pass

            if not cycle_failed:
                details = compose_alerts_inline(_ALERTS_STATE)
                if details and details != "none":
                    summary["alerts_inline"] = details
                else:
                    summary["alerts_inline"] = summary.get("monitors_inline", "none")
            else:
                summary["alerts_inline"] = "fail 1/1 error"
            try:
                errors = sum(1 for state in _MON_STATE.values() if str(state).upper() == "FAIL")
                if cycle_failed:
                    errors += 1
                summary["errors_count"] = int(errors)
            except Exception:
                if cycle_failed:
                    summary["errors_count"] = 1
            try:
                _enrich_summary_from_locker(summary, dl)
            except Exception:
                logging.exception("Failed to enrich sonic summary")
            if icon_line:
                summary.setdefault("positions_icon_line", icon_line)
                set_positions_icon_line(
                    line=icon_line,
                    updated_iso=summary.get("positions_updated_at"),
                    reason=None,
                )
            cfg = {}
            try:
                cfg = dl.system.get_var("sonic_monitor") or {}
            except Exception:
                logging.debug("Failed to load sonic_monitor config", exc_info=True)

            # extra breathing room between last monitor tick and the endcap
            print()
            summary = snapshot_into(summary)
            emit_compact_cycle(
                summary,
                cfg,
                interval,
                enable_color=True,
            )

            # Visual separation between cycles
            print()

            sleep_time = max(interval - elapsed, 0)
            if sleep_time > 0:
                time.sleep(sleep_time)
    except KeyboardInterrupt:
        logging.info("SonicMonitor terminated by user.")
    finally:
        try:
            loop.close()
        except Exception:
            pass


if __name__ == "__main__":
    run_monitor()
