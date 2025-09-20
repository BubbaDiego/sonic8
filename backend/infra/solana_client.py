from solana.rpc.async_api import AsyncClient

from backend.config.rpc import helius_url, redacted, key_fingerprint


def get_async_client() -> AsyncClient:
    url = helius_url()
    print(f"[rpc] using {redacted(url)} (key {key_fingerprint()})")
    return AsyncClient(url, commitment="processed")
