import json
import os
from pathlib import Path


PLACEHOLDER_VALUES = {"<YOUR_KEY>", "YOUR_KEY", "changeme"}


def _config_candidates() -> list[str]:
    """Return config locations to check for Helius credentials.

    Order of precedence:

    1. ``$XCOM_CONFIG_JSON``
    2. ``backend/config/xcom_config.json``
    3. ``config/xcom_config.json``
    4. ``backend/core/xcom_core/xcom_config.json``
    """

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
    unique_paths: list[str] = []
    for path in paths:
        if path and path not in seen:
            seen.add(path)
            unique_paths.append(path)

    return unique_paths


def _read_key() -> str:
    key = (os.getenv("HELIUS_API_KEY") or "").strip()
    if key and "placeholder" not in key.lower() and key not in PLACEHOLDER_VALUES:
        return key

    for candidate in _config_candidates():
        try:
            with open(candidate, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            continue

        value = (data.get("HELIUS_API_KEY") or "").strip()
        if value:
            return value

    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
        key = (os.getenv("HELIUS_API_KEY") or "").strip()
        if key:
            return key
    except Exception:
        pass

    raise RuntimeError(
        "HELIUS_API_KEY missing/placeholder. Set it in env/.env or xcom_config.json."
    )


def helius_url() -> str:
    """Single source of truth for the Helius RPC URL."""
    return f"https://rpc.helius.xyz/?api-key={_read_key()}"


def redacted(url: str) -> str:
    base, _, _ = url.partition("?")
    return f"{base}?api-key=***REDACTED***"


def key_fingerprint() -> str:
    """Log-safe fingerprint of the key, helps confirm same key across processes."""
    k = _read_key()
    return f"{len(k)}:{k[:3]}…{k[-3:]}"
