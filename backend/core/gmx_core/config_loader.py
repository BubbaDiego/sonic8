import os
import json
from typing import Any, Dict, List, Tuple

try:
    import yaml  # PyYAML
except Exception as e:  # pragma: no cover
    yaml = None

class ConfigError(RuntimeError):
    pass

def _parse_scalar(value: str) -> Any:
    low = value.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in {"null", "none", "~"}:
        return None
    if value.startswith(("[", "{")) and value.endswith(("]", "}")):
        try:
            return json.loads(value)
        except Exception:
            pass
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        if "." in value or "e" in value or "E" in value:
            return float(value)
        return int(value)
    except ValueError:
        return value

def _guess_container(lines: List[str], index: int, current_indent: int) -> Any:
    for j in range(index + 1, len(lines)):
        nxt = lines[j]
        stripped = nxt.strip()
        if not stripped or stripped.startswith("#"):
            continue
        next_indent = len(nxt) - len(nxt.lstrip(" "))
        if next_indent <= current_indent:
            return {}
        return [] if stripped.startswith("- ") else {}
    return {}

def _basic_yaml_load(text: str) -> Dict[str, Any]:
    root: Dict[str, Any] = {}
    stack: List[Tuple[int, Any]] = [(-1, root)]
    lines = text.splitlines()

    for idx, raw in enumerate(lines):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        line = raw.strip()

        if line.startswith("- "):
            if not isinstance(parent, list):
                raise ConfigError("Invalid YAML structure: list item without list context")
            item = line[2:].strip()
            if item:
                parent.append(_parse_scalar(item))
            else:
                new_map: Dict[str, Any] = {}
                parent.append(new_map)
                stack.append((indent, new_map))
            continue

        if ":" not in line:
            raise ConfigError(f"Invalid YAML line: {line}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        if isinstance(parent, list):
            raise ConfigError("Invalid YAML structure: key/value inside list item")

        if value == "":
            container = _guess_container(lines, idx, indent)
            parent[key] = container
            stack.append((indent, container))
        else:
            parent[key] = _parse_scalar(value)

    return root

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
    if not os.path.exists(path):
        raise ConfigError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw_text = f.read()
    if yaml is not None:
        raw = yaml.safe_load(raw_text) or {}
    else:
        raw = _basic_yaml_load(raw_text)
    return _resolve_env(raw)

def get_chain_cfg(cfg: Dict[str, Any], chain_key: str) -> Dict[str, Any]:
    chains = (cfg or {}).get("chains") or {}
    if chain_key not in chains:
        raise ConfigError(f"Unknown chain key: {chain_key!r}. Available: {list(chains.keys())}")
    return chains[chain_key]

def pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, default=str)
