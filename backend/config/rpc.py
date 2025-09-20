import os


def _read_key() -> str:
    key = os.getenv("HELIUS_API_KEY", "").strip()
    if not key or key in {"<YOUR_KEY>", "YOUR_KEY", "changeme"}:
        raise RuntimeError("HELIUS_API_KEY missing/placeholder. Set it in .env or env.")
    return key


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
