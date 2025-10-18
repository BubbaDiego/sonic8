from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from backend.config.config_loader import get_config, _load_json_config  # noqa: F401

def read_monitor_threshold_sources(dl) -> Tuple[Dict[str, Any], str]:
    """
    Probe monitor thresholds from (in order): DL.system_vars → global_config → ENV.
    Returns (sources_dict, source_label) where label is 'DL.system_vars' | 'global_config' | 'env' | 'mixed' | ''.
    """
    if not dl:
        return {}, ""

    sysvars = getattr(dl, "system", None)
    gconf   = getattr(dl, "global_config", None)
    used: set[str] = set()

    def _get(key: str):
        if sysvars is not None:
            try:
                v = sysvars.get_var(key)
            except Exception:
                v = None
            if v is not None:
                used.add("DL.system_vars"); return v
        if gconf is not None:
            try:
                v = gconf.get(key)
            except Exception:
                v = None
            if v is not None:
                used.add("global_config"); return v
        v = os.getenv(key)
        if v is not None:
            used.add("env"); return v
        return None

    def _collect(mapping: Dict[str, tuple[str, ...] | str]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for short, keys in mapping.items():
            cands = (keys,) if isinstance(keys, str) else tuple(keys)
            for k in cands:
                val = _get(k)
                if val is not None:
                    out[short] = val
                    break
        return out

    profit = _collect({
        "pos": ("profit_position_threshold", "profit_threshold", "profit_badge_value"),
        "pf":  ("profit_portfolio_threshold", "profit_total_threshold", "profit_total"),
    })
    liquid = _collect({
        "btc": ("liquid_threshold_btc", "liquid_threshold", "liquid_threshold_BTC"),
        "eth": ("liquid_threshold_eth", "liquid_threshold_ETH"),
        "sol": ("liquid_threshold_sol", "liquid_threshold_SOL"),
    })
    market = _collect({
        "btc": ("market_delta_btc", "market_delta_BTC"),
        "eth": ("market_delta_eth", "market_delta_ETH"),
        "sol": ("market_delta_sol", "market_delta_SOL"),
        "rearm": ("market_rearm_mode",),
        "sonic": ("market_sonic_state",),
    })

    if not used:
        label = ""
    elif len(used) == 1:
        label = next(iter(used))
    else:
        label = "mixed: " + " + ".join(sorted(used))

    return {"profit": profit, "liquid": liquid, "market": market}, label


def _as_dict(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return {}


def _probe_env(name: str) -> Optional[str]:
    return os.getenv(name)


def _probe_sysvars(dl, name: str) -> Any:
    try:
        system = getattr(dl, "system", None)
        return system.get_var(name) if system else None
    except Exception:
        return None


def _probe_gconf(dl, name: str) -> Any:
    try:
        gconf = getattr(dl, "global_config", None)
        return gconf.get(name) if gconf else None
    except Exception:
        return None


def _probe_json(name: str, json_obj: Dict[str, Any]) -> Any:
    if name in json_obj:
        return json_obj.get(name)
    for bucket in ("profit_monitor", "liquid_monitor", "monitors", "monitor"):
        node = _as_dict(json_obj.get(bucket))
        if name in node:
            return node.get(name)
    return None


def trace_monitor_thresholds(dl) -> Dict[str, List[Tuple[str, str, Any, bool]]]:
    """
    Returns a dict with 'profit' and 'liquid', each a list of tuples:
      (source, keypath, value, used)
    Only one item per monitor will have used=True (the chosen value after precedence).
    Precedence (highest last): ENV_OVERRIDES/DB snapshot < ENV < JSON   (JSON rules)
    """

    json_obj, json_path = _load_json_config()
    merged = get_config()

    def choose(keys: Tuple[str, ...]) -> List[Tuple[str, str, Any, bool]]:
        rows: List[Tuple[str, str, Any, bool]] = []
        found: Dict[str, Tuple[str, Any]] = {}
        for k in keys:
            sysv = _probe_sysvars(dl, k)
            if sysv is not None:
                found.setdefault("DB", (k, sysv))
            gcv = _probe_gconf(dl, k)
            if gcv is not None:
                found.setdefault("DB(gconf)", (k, gcv))
            envv = _probe_env(k.upper())
            if envv is not None:
                found.setdefault("ENV", (k.upper(), envv))
            jsv = _probe_json(k, json_obj)
            if jsv is not None:
                found.setdefault("JSON", (f"{json_path or '<json>'}:{k}", jsv))

            merged_val = merged.get(k)
            if merged_val is not None and "JSON" not in found:
                found.setdefault("JSON", (k, merged_val))

        winner_src = None
        for src in ("JSON", "ENV", "DB", "DB(gconf)"):
            if src in found:
                winner_src = src
                break

        for src in ("DB", "DB(gconf)", "ENV", "JSON"):
            if src in found:
                kp, val = found[src]
                rows.append((src, kp, val, src == winner_src))
        return rows

    profit_keys: Dict[str, Tuple[str, ...]] = {
        "pos": ("profit_position_threshold", "profit_threshold", "profit_badge_value"),
        "pf": ("profit_portfolio_threshold", "profit_total_threshold", "profit_total"),
    }
    liquid_keys: Dict[str, Tuple[str, ...]] = {
        "btc": ("liquid_threshold_btc", "liquid_threshold_BTC", "liquid_threshold"),
        "eth": ("liquid_threshold_eth", "liquid_threshold_ETH", "liquid_threshold"),
        "sol": ("liquid_threshold_sol", "liquid_threshold_SOL", "liquid_threshold"),
    }

    trace = {"profit": [], "liquid": []}
    for keys in profit_keys.values():
        trace["profit"].extend(choose(keys))
    for keys in liquid_keys.values():
        trace["liquid"].extend(choose(keys))

    return trace
