from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ---- Lightweight JSON probe (no dependency on config_loader) -----------------

_ENV_JSON_PATH = "SONIC_CONFIG_JSON"
_JSON_CANDIDATES = (
    "backend/config/sonic_monitor_config.json",
    "config/sonic_monitor_config.json",
)

def _first_existing(paths: Iterable[str]) -> Optional[Path]:
    for p in paths:
        pp = Path(p).expanduser()
        if pp.exists():
            return pp
    return None


def _load_json_config_light() -> Tuple[Dict[str, Any], Optional[Path]]:
    env_path = os.getenv(_ENV_JSON_PATH)
    if env_path:
        p = Path(env_path).expanduser()
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8")), p
            except Exception:
                pass  # fall through to candidates
    cand = _first_existing(_JSON_CANDIDATES)
    if not cand:
        return {}, None
    try:
        obj = json.loads(cand.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}, cand
    except Exception:
        return {}, cand


# ---- DB/ENV/JSON probing helpers --------------------------------------------

def _probe_sysvars(dl: Any, key: str) -> Any:
    try:
        sys = getattr(dl, "system", None)
        return sys.get_var(key) if sys else None
    except Exception:
        return None


def _probe_gconf(dl: Any, key: str) -> Any:
    try:
        g = getattr(dl, "global_config", None)
        return g.get(key) if g else None
    except Exception:
        return None


def _probe_env(key: str) -> Any:
    # ENV keys are usually uppercased
    return os.getenv(key.upper())


def _find_key_recursive(obj: Any, target: str) -> Any:
    """Find first value for key == target anywhere in a JSON object, recursively."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() == target.lower():
                return v
            found = _find_key_recursive(v, target)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_key_recursive(v, target)
            if found is not None:
                return found
    return None


def _probe_json(json_obj: Dict[str, Any], key: str) -> Any:
    """
    Try both exact-name lookups (for flat configs) and common nested patterns:
      liquid_threshold_btc  → look under {liquid/liq/liquidation}.{thresholds}.{BTC/btc}
    """
    # 1) Exact key anywhere
    val = _find_key_recursive(json_obj, key)
    if val is not None:
        return val

    # 2) Heuristic for per-asset thresholds in nested maps
    if key.lower().startswith("liquid_threshold_"):
        asset = key.split("_")[-1].upper()
        for bucket in ("liquid", "liquidation", "liquid_monitor", "monitors"):
            node = _find_key_recursive(json_obj, bucket)
            if isinstance(node, dict):
                # common shapes: {thresholds:{BTC:6.0}}, {BTC:{threshold:6.0}}
                thresholds = node.get("thresholds") if isinstance(node, dict) else None
                if isinstance(thresholds, dict) and asset in thresholds:
                    return thresholds.get(asset)
                if asset in node and isinstance(node[asset], dict):
                    cand = node[asset].get("threshold")
                    if cand is not None:
                        return cand
    return None


# ---- Public trace API --------------------------------------------------------

_PRECEDENCE = ("JSON", "ENV", "DB", "DB(gconf)")  # JSON wins (your rule)


def _collect_for_keys(
    dl: Any,
    json_obj: Dict[str, Any],
    keys: Iterable[str],
) -> List[Tuple[str, str, Any, bool]]:
    """
    Return a list of rows (source, keypath, value, used) for the given keys.
    Only one row will have used=True according to _PRECEDENCE.
    """
    found: Dict[str, Tuple[str, Any]] = {}
    for k in keys:
        db = _probe_sysvars(dl, k)
        if db is not None and "DB" not in found:
            found["DB"] = (k, db)
        g = _probe_gconf(dl, k)
        if g is not None and "DB(gconf)" not in found:
            found["DB(gconf)"] = (k, g)
        ev = _probe_env(k)
        if ev is not None and "ENV" not in found:
            found["ENV"] = (k, ev)
        jv = _probe_json(json_obj, k)
        if jv is not None and "JSON" not in found:
            # include a pseudo keypath to show origin
            found["JSON"] = (k, jv)

    # Winner by precedence
    winner = None
    for src in _PRECEDENCE:
        if src in found:
            winner = src
            break

    rows: List[Tuple[str, str, Any, bool]] = []
    for src in ("DB", "DB(gconf)", "ENV", "JSON"):
        if src in found:
            kp, val = found[src]
            rows.append((src, kp, val, src == winner))
    return rows


def trace_monitor_thresholds(dl: Any) -> Dict[str, List[Tuple[str, str, Any, bool]]]:
    """
    Return a dict with two keys, 'profit' and 'liquid'.
    Each maps to a list of (source, key, value, used) rows.
    """
    json_obj, _ = _load_json_config_light()

    PROFIT_KEYS_POS = ("profit_position_threshold", "profit_threshold", "profit_badge_value")
    PROFIT_KEYS_PF  = ("profit_portfolio_threshold", "profit_total_threshold", "profit_total")
    LIQ_KEYS_BTC    = ("liquid_threshold_btc", "liquid_threshold_BTC", "liquid_threshold")
    LIQ_KEYS_ETH    = ("liquid_threshold_eth", "liquid_threshold_ETH", "liquid_threshold")
    LIQ_KEYS_SOL    = ("liquid_threshold_sol", "liquid_threshold_SOL", "liquid_threshold")

    trace: Dict[str, List[Tuple[str, str, Any, bool]]] = {
        "profit": [],
        "liquid": [],
    }
    trace["profit"].extend(_collect_for_keys(dl, json_obj, PROFIT_KEYS_POS))
    trace["profit"].extend(_collect_for_keys(dl, json_obj, PROFIT_KEYS_PF))
    trace["liquid"].extend(_collect_for_keys(dl, json_obj, LIQ_KEYS_BTC))
    trace["liquid"].extend(_collect_for_keys(dl, json_obj, LIQ_KEYS_ETH))
    trace["liquid"].extend(_collect_for_keys(dl, json_obj, LIQ_KEYS_SOL))
    return trace


def pretty_print_trace(trace: Dict[str, List[Tuple[str, str, Any, bool]]]) -> None:
    """Optional helper to dump a human-friendly trace block."""

    def _fmt(v: Any) -> str:
        return "—" if v in (None, "") else str(v)

    print("   🔎 Trace (winner per setting is marked)")
    for mon in ("profit", "liquid"):
        rows = trace.get(mon, [])
        if not rows:
            continue
        print(f"     {mon}:")
        for src, key, val, used in rows:
            tick = "✓" if used else "·"
            print(f"       {tick} {src:<8s} {key} = {_fmt(val)}")
