import os
import json
from typing import Any, Dict

try:
    import yaml  # PyYAML
except Exception as e:  # pragma: no cover
    yaml = None

class ConfigError(RuntimeError):
    pass

def _resolve_env(val: Any) -> Any:
    if isinstance(val, str) and val.startswith("ENV:"):
        env_key = val.split("ENV:", 1)[1].strip()
        v = os.environ.get(env_key)
        if v is None or v == "":
            raise ConfigError(f"Missing required environment variable: {env_key}")
        return v
    if isinstance(val, dict):
        return {k: _resolve_env(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_resolve_env(v) for v in val]
    return val

def load_config(path: str) -> Dict[str, Any]:
    if yaml is None:
        raise ConfigError("PyYAML is required. Install with `pip install PyYAML`.")
    if not os.path.exists(path):
        raise ConfigError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return _resolve_env(raw)

def get_chain_cfg(cfg: Dict[str, Any], chain_key: str) -> Dict[str, Any]:
    chains = (cfg or {}).get("chains") or {}
    if chain_key not in chains:
        raise ConfigError(f"Unknown chain key: {chain_key!r}. Available: {list(chains.keys())}")
    return chains[chain_key]

def pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, default=str)
