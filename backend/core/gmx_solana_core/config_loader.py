import os
import json
from typing import Any, Dict

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

class ConfigError(RuntimeError):
    pass

def _resolve_env(val: Any) -> Any:
    """Resolve ENV:FOO placeholders recursively inside the solana subtree."""
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

def load_solana_config(path: str) -> Dict[str, Any]:
    """Load only the 'solana' subtree and resolve ENV placeholders there."""
    if yaml is None:
        raise ConfigError("PyYAML required. Install with: pip install PyYAML")
    if not os.path.exists(path):
        raise ConfigError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    sol = (raw or {}).get("solana")
    if not sol:
        raise ConfigError("Missing 'solana' section in config.")
    return _resolve_env(sol)

def pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, default=str)
