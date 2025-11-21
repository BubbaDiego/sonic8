from __future__ import annotations
from pathlib import Path
from typing import Any, Dict

from backend.config.config_loader import load_config_json_only
from backend.core import config_oracle as ConfigOracle

_CFG: Dict[str, Any] | None = None
_CFG_PATH = Path(__file__).resolve().parents[2] / "config" / "sonic_monitor_config.json"
# e.g., .../backend/config/sonic_monitor_config.json

def load() -> Dict[str, Any]:
    """JSON-only source of truth."""
    global _CFG
    if _CFG is None:
        _CFG = load_config_json_only(str(_CFG_PATH))
    return _CFG

# ---- Helpers ----------------------------------------------------------------


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "":
            return default
        return lowered in {"1", "true", "yes", "on"}
    return bool(value)


# ---- Tiny getters (all FILE-origin) -----------------------------------------
def get_loop_seconds(default: int = 60) -> int:
    """
    Poll interval for the Sonic monitor loop.

    Oracle-first:
      1) ConfigOracle global monitor config.loop_seconds
      2) Legacy JSON monitor.loop_seconds / monitor.interval_seconds
      3) Provided default
    """
    # 1) Oracle view (includes env overlays via EnvMonitorOverlayProvider)
    try:
        global_cfg = ConfigOracle.get_global_monitor_config()
        if global_cfg and global_cfg.loop_seconds:
            iv = int(global_cfg.loop_seconds)
            if iv > 0:
                return iv
    except Exception:  # pragma: no cover - defensive
        pass

    # 2) Legacy JSON-only config
    cfg = load()
    try:
        mon = cfg.get("monitor") or {}
        val = mon.get("loop_seconds") or mon.get("interval_seconds") or default
        v = int(val)
        return v if v > 0 else default
    except Exception:
        return default

def get_enabled_monitors() -> Dict[str, bool]:
    raw = load().get("monitor", {}).get("enabled", {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): bool(v) for k, v in raw.items()}


def get_monitor_log_success(default: bool = False) -> bool:
    monitor = load().get("monitor", {})
    value = monitor.get("log_success")
    if value is None:
        value = monitor.get("notify_on_success")
    return _coerce_bool(value, default)

def get_db_path() -> str | None:
    value = load().get("database", {}).get("path")
    return str(value) if value is not None else None

def get_xcom_live() -> bool:
    """
    Static config view of the XCom 'live' flag.

    Oracle-first:
      - ConfigOracle global monitor config.xcom_live

    Legacy fallback:
      - monitor.xcom_live in the JSON file
    """
    # 1) Oracle view (env overlays already applied by load_monitor_config)
    try:
        global_cfg = ConfigOracle.get_global_monitor_config()
        if global_cfg and global_cfg.xcom_live is not None:
            return bool(global_cfg.xcom_live)
    except Exception:  # pragma: no cover - defensive
        pass

    # 2) Legacy JSON-only view
    cfg = load()
    try:
        mon = cfg.get("monitor") or {}
        return bool(mon.get("xcom_live", True))
    except Exception:
        return True


def should_force_price_sync() -> bool:
    cfg = load()
    price_cfg = cfg.get("price", {})
    monitor_cfg = cfg.get("monitor", {})
    legacy_cfg = cfg.get("price_monitor", {})
    value = price_cfg.get("force_sync")
    if value is None:
        value = monitor_cfg.get("force_price_sync")
    if value is None:
        value = legacy_cfg.get("force_sync")
    return _coerce_bool(value, False)


def should_force_position_sync() -> bool:
    cfg = load()
    position_cfg = cfg.get("position", {})
    monitor_cfg = cfg.get("monitor", {})
    legacy_cfg = cfg.get("position_monitor", {})
    value = position_cfg.get("force_sync")
    if value is None:
        value = monitor_cfg.get("force_position_sync")
    if value is None:
        value = legacy_cfg.get("force_sync")
    return _coerce_bool(value, False)

def get_channels() -> Dict[str, Dict[str, bool]]:
    return dict(load().get("channels", {}))

def get_liquid_thresholds() -> Dict[str, float]:
    """
    Return per-asset liquidation thresholds from config.

    Preference order:
        1) liquid_monitor.thresholds   (new Sonic monitor schema)
        2) liquid.thresholds           (legacy schema)
    Values are normalized to uppercase keys (e.g. "BTC", "ETH", "SOL").
    """
    cfg = load()

    # 1) Prefer new layout: liquid_monitor.thresholds.{SYMBOL}
    src: Dict[str, Any] = {}
    liquid_monitor = cfg.get("liquid_monitor") or {}
    if isinstance(liquid_monitor, dict):
        cand = liquid_monitor.get("thresholds")
        if isinstance(cand, dict):
            src = cand

    # 2) Fallback: legacy layout liquid.thresholds.{SYMBOL}
    if not src:
        liquid_legacy = cfg.get("liquid") or {}
        if isinstance(liquid_legacy, dict):
            cand = liquid_legacy.get("thresholds")
            if isinstance(cand, dict):
                src = cand

    out: Dict[str, float] = {}
    if isinstance(src, dict):
        for key, value in src.items():
            try:
                out[str(key).upper()] = float(value)
            except Exception:
                # Ignore malformed values, keep rest
                continue

    return out

def get_liquid_blasts() -> Dict[str, int]:
    raw = load().get("liquid", {}).get("blast", {})
    output: Dict[str, int] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            try:
                output[str(key).upper()] = int(value)
            except Exception:
                continue
    return output

def get_market_config() -> Dict[str, Any]:
    return dict(load().get("market", {}))

def get_price_assets() -> list[str]:
    assets = load().get("price", {}).get("assets", [])
    result: list[str] = []
    if isinstance(assets, (list, tuple)):
        for asset in assets:
            text = str(asset).strip().upper()
            if text:
                result.append(text)
    return result

def get_profit_config() -> Dict[str, Any]:
    """
    Profit monitor thresholds (FILE-origin).

    Returns a dict that always exposes:
        - position_usd
        - portfolio_usd

    Values are derived from, in order:
        1) profit_monitor.position_profit_usd / portfolio_profit_usd
        2) profit.position_profit_usd / portfolio_profit_usd
        3) profit.position_usd / portfolio_usd

    This mirrors how the runtime monitor resolves thresholds, but is
    FILE-only (no DB access) so it is safe for the startup banner.
    """
    cfg = load()

    # Start from the raw "profit" block so existing fields (notifications,
    # snooze_seconds, etc.) are preserved.
    profit_cfg: Dict[str, Any] = {}
    raw_profit = cfg.get("profit") or {}
    if isinstance(raw_profit, dict):
        profit_cfg.update(raw_profit)

    pm = cfg.get("profit_monitor") or {}

    pos_val: Any = None
    pf_val: Any = None

    # 1) Canonical config: profit_monitor.*
    if isinstance(pm, dict):
        pos_val = pm.get("position_profit_usd")
        pf_val = pm.get("portfolio_profit_usd")

    # 2) Legacy-style keys under "profit"
    if pos_val is None and isinstance(raw_profit, dict):
        pos_val = raw_profit.get("position_profit_usd")
    if pf_val is None and isinstance(raw_profit, dict):
        pf_val = raw_profit.get("portfolio_profit_usd") or raw_profit.get("portfolio_usd")

    # 3) Generic position_usd/portfolio_usd if present
    if pos_val is None and isinstance(raw_profit, dict):
        pos_val = raw_profit.get("position_usd")
    if pf_val is None and isinstance(raw_profit, dict):
        pf_val = raw_profit.get("portfolio_usd")

    # Normalize to floats on the keys the banner expects
    try:
        if pos_val is not None:
            profit_cfg["position_usd"] = float(pos_val)
    except Exception:
        pass
    try:
        if pf_val is not None:
            profit_cfg["portfolio_usd"] = float(pf_val)
    except Exception:
        pass

    return profit_cfg

def get_twilio() -> Dict[str, str]:
    cfg = dict(load().get("twilio", {}))
    return {
        "SID": str(cfg.get("account_sid") or cfg.get("sid") or ""),
        "AUTH": str(cfg.get("auth_token") or cfg.get("token") or ""),
        "FROM": str(cfg.get("from") or cfg.get("from_phone") or ""),
        "TO": str(cfg.get("to") or cfg.get("to_phone") or ""),
    }
