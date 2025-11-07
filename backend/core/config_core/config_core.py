from __future__ import annotations

import copy
from typing import Dict, Any, Tuple, Optional

from .precedence import PrecedencePolicy
from .providers import json_provider, db_provider, env_provider
from .validators import validate_sonic_monitor

# === Default config: EXACTLY as specified ===
DEFAULT_SONIC_MONITOR_CONFIG: Dict[str, Any] = {
    "monitor": {
        "loop_seconds": 30,
        "enabled": {
            "sonic": True,
            "liquid": True,
            "profit": True,
            "market": True,
            "price": True
        },
        "xcom_live": True
    },
    "liquid": {
        "notifications": {
            "system": True,
            "voice": True,
            "sms": True,
            "tts": True
        },
        "blast": {"BTC": 5, "ETH": 5, "SOL": 5}
    },
    "profit": {
        "notifications": {
            "system": True,
            "voice": True,
            "sms": False,
            "tts": True
        },
        "snooze_seconds": 1200
    },
    "market": {
        "notifications": {"system": False, "voice": False, "sms": False, "tts": False}
    },
    "price": {
        "notifications": {"system": False, "voice": False, "sms": False, "tts": False}
    },
    "liquid_monitor": {
        "thresholds": {"BTC": 1.3, "ETH": 1.0, "SOL": 11.5},
        "blast": {"BTC": 5, "ETH": 5, "SOL": 5}
    },
    "profit_monitor": {
        "snooze_seconds": 1200,
        "position_profit_usd": 10,
        "portfolio_profit_usd": 40
    }
}


def _deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    """Recursive 'overlay onto base' (overlay wins)."""
    for k, v in (overlay or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = copy.deepcopy(v)
    return base


def _normalize(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate legacy keys to the new shape (idempotent)."""
    lm = cfg.get("liquid_monitor")
    if isinstance(lm, dict) and "asset_thresholds" in lm and "thresholds" not in lm:
        lm["thresholds"] = dict(lm["asset_thresholds"])
    return cfg


class ConfigCore:
    """
    Facade for loading/saving configuration with explicit precedence.
    Precedence defaults to JSON -> DB -> ENV (JSON has highest priority).
    """

    def __init__(self, policy: PrecedencePolicy = PrecedencePolicy.JSON_FIRST, json_path: Optional[str] = None):
        self.policy = policy
        self.json_path = json_path  # allow custom JSON location if desired

    def set_precedence(self, policy: PrecedencePolicy) -> None:
        self.policy = policy

    # -------- Public API --------

    def load(self, name: str = "sonic_monitor") -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if name != "sonic_monitor":
            raise NotImplementedError("Only 'sonic_monitor' is supported for now.")

        json_cfg, json_src = json_provider.read_config(self.json_path)
        db_cfg, db_src     = db_provider.read_config()
        env_cfg, env_src   = env_provider.read_overlay()

        # Start with defaults, then apply layers in precedence order:
        # we merge in this order: env -> db -> json, so later wins (JSON highest).
        effective: Dict[str, Any] = _normalize(copy.deepcopy(DEFAULT_SONIC_MONITOR_CONFIG))
        for layer in self.policy.order():
            if layer == "env" and env_cfg:
                _deep_merge(effective, _normalize(copy.deepcopy(env_cfg)))
            elif layer == "db" and db_cfg:
                _deep_merge(effective, _normalize(copy.deepcopy(db_cfg)))
            elif layer == "json" and json_cfg:
                _deep_merge(effective, _normalize(copy.deepcopy(json_cfg)))

        errors, warnings = validate_sonic_monitor(effective)
        meta = {
            "sources": {"json": json_src, "db": db_src, "env": env_src},
            "policy": self.policy.name,
            "errors": errors,
            "warnings": warnings,
        }
        return effective, meta

    def save(self, name: str, cfg: Dict[str, Any], also_write_legacy: bool = True) -> Dict[str, Any]:
        if name != "sonic_monitor":
            raise NotImplementedError("Only 'sonic_monitor' is supported for now.")

        cfg = _normalize(copy.deepcopy(cfg))
        errors, warnings = validate_sonic_monitor(cfg)
        if errors:
            return {"ok": False, "errors": errors, "warnings": warnings}

        ok_json, json_path = json_provider.write_config(cfg, self.json_path)
        ok_db, db_key      = db_provider.write_config(cfg, also_write_legacy=also_write_legacy)

        return {
            "ok": bool(ok_json and ok_db),
            "json_path": json_path,
            "db_key": db_key,
            "errors": [],
            "warnings": warnings,
        }

    def get(self, name: str, dotted_path: str, default: Any = None) -> Any:
        cfg, _ = self.load(name)
        cur: Any = cfg
        for part in dotted_path.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur
