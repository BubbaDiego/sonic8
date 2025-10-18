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
                pass
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
    return os.getenv(key.upper())


def _find_key_recursive(obj: Any, target: str) -> Any:
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
    # 1) exact key anywhere
    val = _find_key_recursive(json_obj, key)
    if val is not None:
        return val
    # 2) heuristic for per-asset liquidation thresholds
    if key.lower().startswith("liquid_threshold_"):
        asset = key.split("_")[-1].upper()
        for bucket in ("liquid", "liquidation", "liquid_monitor", "monitors"):
            node = _find_key_recursive(json_obj, bucket)
            if isinstance(node, dict):
                thresholds = node.get("thresholds") if isinstance(node, dict) else None
                if isinstance(thresholds, dict) and asset in thresholds:
                    return thresholds.get(asset)
                if asset in node and isinstance(node[asset], dict):
                    cand = node[asset].get("threshold")
                    if cand is not None:
                        return cand
    return None


# ---- precedence & collectors -------------------------------------------------

_PRECEDENCE = ("JSON", "ENV", "DB", "DB(gconf)")  # JSON wins last


def _collect_for_keys(dl: Any, json_obj: Dict[str, Any], keys: Iterable[str]) -> List[Tuple[str, str, Any, bool]]:
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
            found["JSON"] = (k, jv)

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


# ---- public API used by sonic_monitor ----------------------------------------

def read_monitor_threshold_sources(dl) -> tuple[dict, str]:
    """
    Return compact per-monitor sources + summary label (for old compact line).
    """
    json_obj, _ = _load_json_config_light()

    def pick(keys: tuple[str, ...]) -> dict:
        rows = _collect_for_keys(dl, json_obj, keys)
        # pick winner by precedence; return its value only (compact view)
        for src in ("JSON", "ENV", "DB", "DB(gconf)"):
            for s, k, v, used in rows:
                if s == src and used:
                    return {"value": v, "source": s}
        return {}

    used = set()

    def mark(src: str):
        if src:
            used.add(src)

    profit_pos = pick(("profit_position_threshold", "profit_threshold", "profit_badge_value"))
    mark(profit_pos.get("source"))
    profit_pf = pick(("profit_portfolio_threshold", "profit_total_threshold", "profit_total"))
    mark(profit_pf.get("source"))

    liq_btc = pick(("liquid_threshold_btc", "liquid_threshold_BTC", "liquid_threshold"))
    mark(liq_btc.get("source"))
    liq_eth = pick(("liquid_threshold_eth", "liquid_threshold_ETH", "liquid_threshold"))
    mark(liq_eth.get("source"))
    liq_sol = pick(("liquid_threshold_sol", "liquid_threshold_SOL", "liquid_threshold"))
    mark(liq_sol.get("source"))

    label = "mixed: " + " + ".join(sorted(used)) if len(used) > 1 else (next(iter(used)) if used else "")
    return {
        "profit": {"pos": profit_pos.get("value"), "pf": profit_pf.get("value")},
        "liquid": {"btc": liq_btc.get("value"), "eth": liq_eth.get("value"), "sol": liq_sol.get("value")},
    }, label


def trace_monitor_thresholds(dl) -> Dict[str, List[Tuple[str, str, Any, bool]]]:
    """
    Detailed rows per setting: (source, key, value, used)
    Exactly one row per setting has used=True.
    """
    json_obj, _ = _load_json_config_light()
    PROFIT_POS = ("profit_position_threshold", "profit_threshold", "profit_badge_value")
    PROFIT_PF = ("profit_portfolio_threshold", "profit_total_threshold", "profit_total")
    LIQ_BTC = ("liquid_threshold_btc", "liquid_threshold_BTC", "liquid_threshold")
    LIQ_ETH = ("liquid_threshold_eth", "liquid_threshold_ETH", "liquid_threshold")
    LIQ_SOL = ("liquid_threshold_sol", "liquid_threshold_SOL", "liquid_threshold")

    out: Dict[str, List[Tuple[str, str, Any, bool]]] = {"profit": [], "liquid": []}
    out["profit"].extend(_collect_for_keys(dl, json_obj, PROFIT_POS))
    out["profit"].extend(_collect_for_keys(dl, json_obj, PROFIT_PF))
    out["liquid"].extend(_collect_for_keys(dl, json_obj, LIQ_BTC))
    out["liquid"].extend(_collect_for_keys(dl, json_obj, LIQ_ETH))
    out["liquid"].extend(_collect_for_keys(dl, json_obj, LIQ_SOL))
    return out


def pretty_print_trace(trace: Dict[str, List[Tuple[str, str, Any, bool]]]) -> None:
    def _fmt(v: Any) -> str:
        return "—" if v in (None, "") else str(v)

    print("   🔎 Trace (winner per setting marked ✓)")
    for mon in ("profit", "liquid"):
        rows = trace.get(mon, [])
        if not rows:
            continue
        print(f"     {mon}:")
        for src, key, val, used in rows:
            tick = "✓" if used else "·"
            print(f"       {tick} {src:<8s} {key} = {_fmt(val)}")
