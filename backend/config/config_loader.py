from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    def load_dotenv(*_a, **_k): return None

logger = logging.getLogger(__name__)

MERGE_PRECEDENCE = ("defaults", "db", "env", "json")  # JSON wins (highest priority)
SENSITIVE_NAME_TOKENS: Tuple[str, ...] = ("SID", "TOKEN", "KEY", "SECRET", "PASSWORD", "PASS", "API", "BEARER")
ENV_JSON_PATH_VAR = "SONIC_CONFIG_JSON"
ENV_OVERRIDES_VAR = "SONIC_CONFIG_OVERRIDES_JSON"

def _deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def _expand_env(obj: Any) -> Any:
    if isinstance(obj, str):
        return os.path.expandvars(os.path.expanduser(obj))
    if isinstance(obj, list):
        return [_expand_env(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _expand_env(v) for k, v in obj.items()}
    return obj

def _contains_unexpanded_vars(value: Any) -> bool:
    if isinstance(value, str):
        return bool(re.search(r"(?<!\\)\$\{[^}]+\}|(?<!\\)\$[A-Za-z_]\w*|%[A-Za-z_]\w*%", value))
    if isinstance(value, dict):
        return any(_contains_unexpanded_vars(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_unexpanded_vars(v) for v in value)
    return False

def _redact_value(key: str, value: Any) -> Any:
    if isinstance(value, str) and any(tok in key.upper() for tok in SENSITIVE_NAME_TOKENS):
        return ("****" if len(value) <= 4 else f"{'*'*4}…{value[-4:]}")
    return value

def _redacted_dict(d: Any) -> Any:
    if isinstance(d, dict):
        return {k: _redacted_dict(v) if isinstance(v, (dict, list)) else _redact_value(k, v) for k, v in d.items()}
    if isinstance(d, list):
        return [_redacted_dict(v) for v in d]
    return d

def _first_existing_path(cands: Iterable[Path]) -> Path | None:
    for p in cands:
        if p and p.exists():
            return p
    return None

def _load_defaults() -> Dict[str, Any]:
    return {"database": {"path": "mother.db"}, "monitors": {}, "twilio": {}, "poll_interval_seconds": 5}

def _load_json_config() -> Tuple[Dict[str, Any], Path | None]:
    env_path = os.getenv(ENV_JSON_PATH_VAR)
    candidates = (
        Path(env_path).expanduser() if env_path else None,
        Path("backend/config/sonic_monitor_config.json"),
        Path("config/sonic_monitor_config.json"),
    )
    chosen = _first_existing_path([c for c in candidates if c])
    if not chosen:
        logger.info("No JSON config file found.")
        return {}, None
    data = json.loads(chosen.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("Top-level JSON must be an object")
    return data, chosen

def _load_env_overrides() -> Dict[str, Any]:
    raw = os.getenv(ENV_OVERRIDES_VAR, "").strip()
    if not raw:
        return {}
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise RuntimeError(f"{ENV_OVERRIDES_VAR} must be a JSON object")
    return obj

def _load_db_config() -> Dict[str, Any]:
    accessors = (
        ("backend.core.monitor_core.config_store", "read_monitor_config"),
        ("backend.core.monitor_core.settings_store", "read_monitor_config"),
        ("backend.core.config_store", "read_monitor_config"),
        ("backend.core.db.config_store", "read_monitor_config"),
    )
    for mod_name, fn_name in accessors:
        try:
            mod = __import__(mod_name, fromlist=[fn_name])
            fn = getattr(mod, fn_name, None)
            if callable(fn):
                cfg = fn()
                if isinstance(cfg, dict):
                    return cfg
        except Exception:
            continue
    return {}

def _assert_min_schema(cfg: Dict[str, Any]) -> None:
    db_path = cfg.get("database", {}).get("path")
    if db_path is None:
        logger.warning("Config missing database.path")
    monitors = cfg.get("monitors", {})
    if monitors is not None and not isinstance(monitors, dict):
        raise RuntimeError("config.monitors must be an object")
    poll = cfg.get("poll_interval_seconds")
    if poll is not None and (not isinstance(poll, (int, float)) or poll <= 0):
        raise RuntimeError("poll_interval_seconds must be positive")

def _assert_no_unexpanded_vars(cfg: Dict[str, Any]) -> None:
    if _contains_unexpanded_vars(cfg):
        raise RuntimeError("Unexpanded environment variable placeholder detected in config (e.g., ${VAR}).")

def redacted_view(cfg: Dict[str, Any]) -> Dict[str, Any]:
    return _redacted_dict(cfg)  # type: ignore[return-value]

def get_config() -> Dict[str, Any]:
    load_dotenv()
    defaults_cfg = _load_defaults()
    db_cfg = _load_db_config()
    env_overrides_cfg = _load_env_overrides()
    json_cfg, json_path = _load_json_config()

    merged = _deep_merge(defaults_cfg, db_cfg)
    merged = _deep_merge(merged, env_overrides_cfg)
    merged = _deep_merge(merged, json_cfg)  # JSON wins

    merged = _expand_env(merged)
    _assert_no_unexpanded_vars(merged)
    _assert_min_schema(merged)
    try:
        which = str(json_path) if json_path else "<none>"
        logger.info("Config loaded. JSON=%s  Precedence=%s", which, " < ".join(MERGE_PRECEDENCE))
    except Exception:
        pass
    return merged

# Alias for existing call sites
load_config = get_config

def print_banner(cfg: Dict[str, Any]) -> None:
    safe = redacted_view({
        "Database": cfg.get("database", {}).get("path", ""),
        "PollInterval": cfg.get("poll_interval_seconds"),
        "Twilio": cfg.get("twilio", {}),
        "Monitors": sorted(list(cfg.get("monitors", {}).keys())),
    })
    print("══════════════════════════════════════════════════════════════")
    print("   🦔 Sonic Monitor Configuration (merged, JSON-top)")
    print("══════════════════════════════════════════════════════════════")
    print(f"Database        : {safe.get('Database', '')}")
    print(f"Poll Interval   : {safe.get('PollInterval', '')}")
    tw = safe.get("Twilio", {})
    if isinstance(tw, dict) and tw:
        sid = tw.get("account_sid", tw.get("SID", tw.get("sid", "")))
        token = tw.get("auth_token", tw.get("TOKEN", tw.get("token", "")))
        from_ = tw.get("from", tw.get("from_phone", "")); to_ = tw.get("to", tw.get("to_phone", ""))
        print(f"Twilio          : {{'SID': {sid!r}, 'TOKEN': {token!r}, 'FROM': {from_!r}, 'TO': {to_!r}}}")
    mons = safe.get("Monitors", [])
    print(f"Monitors        : {', '.join(mons) if mons else '(none)'}")
    print("══════════════════════════════════════════════════════════════")
