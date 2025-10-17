from __future__ import annotations
import os, json
from typing import Any, Dict, List, Tuple, Optional
from backend.config.config_loader import get_config, _load_json_config  # _load_json_config is safe to import

# Which keys we probe for each monitor:
PROFIT_KEYS = {
    "pos": ("profit_position_threshold", "profit_threshold", "profit_badge_value"),
    "pf":  ("profit_portfolio_threshold", "profit_total_threshold", "profit_total"),
}
LIQUID_KEYS = {
    "btc": ("liquid_threshold_btc", "liquid_threshold_BTC", "liquid_threshold"),
    "eth": ("liquid_threshold_eth", "liquid_threshold_ETH", "liquid_threshold"),
    "sol": ("liquid_threshold_sol", "liquid_threshold_SOL", "liquid_threshold"),
}

def _as_dict(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict): return raw
    if isinstance(raw, str):
        try: return json.loads(raw)
        except Exception: return {}
    return {}

def _probe_env(name: str) -> Optional[str]:
    return os.getenv(name)

def _probe_sysvars(dl, name: str) -> Any:
    try:
        return getattr(dl, "system", None).get_var(name) if getattr(dl, "system", None) else None
    except Exception:
        return None

def _probe_gconf(dl, name: str) -> Any:
    try:
        return getattr(dl, "global_config", None).get(name) if getattr(dl, "global_config", None) else None
    except Exception:
        return None

def _probe_json(name: str, json_obj: Dict[str, Any]) -> Any:
    # flat and nested (profit_monitor/liquid_monitor) support
    if name in json_obj: return json_obj.get(name)
    # common nested spots:
    for bucket in ("profit_monitor", "liquid_monitor", "monitors", "monitor"):
        node = _as_dict(json_obj.get(bucket))
        if name in node: return node.get(name)
    return None

def trace_monitor_thresholds(dl) -> Dict[str, List[Tuple[str, str, Any, bool]]]:
    """
    Returns a dict with 'profit' and 'liquid', each a list of tuples:
      (source, keypath, value, used)
    Only one item per monitor will have used=True (the chosen value after precedence).
    Precedence (highest last): ENV_OVERRIDES/DB snapshot < ENV < JSON   (JSON rules)
    """
    # Load current JSON (raw) for provenance; merged config is for the 'winner'
    json_obj, json_path = _load_json_config()
    merged = get_config()

    def choose(keys: Tuple[str, ...]) -> List[Tuple[str, str, Any, bool]]:
        rows: List[Tuple[str, str, Any, bool]] = []
        # Collect candidates
        found: Dict[str, Tuple[str, Any]] = {}
        for k in keys:
            sysv = _probe_sysvars(dl, k)
            if sysv is not None: found.setdefault("DB", (k, sysv))
            gcv = _probe_gconf(dl, k)
            if gcv is not None: found.setdefault("DB(gconf)", (k, gcv))
            envv = _probe_env(k.upper())
            if envv is not None: found.setdefault("ENV", (k.upper(), envv))
            jsv = _probe_json(k, json_obj)
            if jsv is not None: found.setdefault("JSON", (f"{json_path or '<json>'}:{k}", jsv))

        # Determine winner by precedence (JSON wins if present)
        winner_src = None
        for src in ("JSON", "ENV", "DB", "DB(gconf)"):
            if src in found:
                winner_src = src
                break

        # Emit trace rows in stable order
        for src in ("DB", "DB(gconf)", "ENV", "JSON"):
            if src in found:
                kp, val = found[src]
                rows.append((src, kp, val, src == winner_src))
        return rows

    # Build traces
    trace = {"profit": [], "liquid": []}
    for label, keys in PROFIT_KEYS.items():
        trace["profit"].extend(choose(tuple(keys)))
    for label, keys in LIQUID_KEYS.items():
        trace["liquid"].extend(choose(tuple(keys)))
    return trace
