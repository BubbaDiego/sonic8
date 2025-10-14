import json
import os
from pathlib import Path


def _config_candidates() -> list[str]:
    paths: list[str] = []
    env_path = os.getenv("XCOM_CONFIG_JSON", "").strip()
    if env_path:
        paths.append(env_path)
    here = Path(__file__).resolve()
    backend_dir = here.parents[1]
    repo_root = here.parents[2]
    paths += [
        str(backend_dir / "config" / "xcom_config.json"),
        str(repo_root / "config" / "xcom_config.json"),
        str(backend_dir / "core" / "xcom_core" / "xcom_config.json"),
    ]
    seen: set[str] = set()
    unique: list[str] = []
    for path in paths:
        if path and path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def _read_key() -> str:
    k = (os.getenv("HELIUS_API_KEY") or "").strip()
    if k and "placeholder" not in k.lower():
        return k
    for candidate in _config_candidates():
        try:
            with open(candidate, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            continue
        v = (data.get("HELIUS_API_KEY") or "").strip()
        if v:
            return v
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
        k = (os.getenv("HELIUS_API_KEY") or "").strip()
        if k:
            return k
    except Exception:
        pass
    raise RuntimeError("HELIUS_API_KEY missing/placeholder. Set it in env/.env or xcom_config.json.")


def helius_url() -> str:
    return f"https://rpc.helius.xyz/?api-key={_read_key()}"


def redacted(url: str) -> str:
    base, _, _ = url.partition("?")
    return f"{base}?api-key=***REDACTED***"


def key_fingerprint() -> str:
    key = _read_key()
    return f"{len(key)}:{key[:3]}…{key[-3:]}"
