import os


def helius_url() -> str:
    """
    Build the Helius RPC URL from the Helius API key in env.
    Raises RuntimeError if the key is missing or still a placeholder.
    """
    key = os.getenv("HELIUS_API_KEY")
    if not key or key.strip() in {"<YOUR_KEY>", "YOUR_KEY", "changeme", ""}:
        raise RuntimeError(
            "HELIUS_API_KEY missing/placeholder. Set it in your environment or .env."
        )
    # Normalize to the canonical endpoint
    return f"https://rpc.helius.xyz/?api-key={key}"


def redacted(url: str) -> str:
    """
    Return a log-safe version of the RPC URL (key redacted).
    """
    base, _, _ = url.partition("?")
    return f"{base}?api-key=***REDACTED***"
