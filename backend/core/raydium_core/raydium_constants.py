# Copyright:
# - Endpoint names/paths below mirror Raydium's official SDK V2 (src/api/url.ts),
#   published under GPL-3.0. We only reference the same strings so our Python
#   client calls the *official* public API routes (no SDK code is embedded).
#   Source: https://app.unpkg.com/@raydium-io/raydium-sdk-v2/.../src/api/url.ts

from __future__ import annotations

# --- Solana Program IDs (public constants) ---
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqCj6mK3dF6YMRGJpDzCkCE7bZt6z7b7"  # SPL Token-2022

# --- Raydium Public API (V3) ---
# Official doc points to the V3 host and Swagger. We default to this host.  # see docs
DEFAULT_RAYDIUM_API_BASE = "https://api-v3.raydium.io"

# These paths mirror the SDK's API_URLS (src/api/url.ts).  # see SDK url.ts
RAYDIUM_API_PATHS = {
    # token APIs
    "TOKEN_LIST": "/mint/list",
    "MINT_INFO_ID": "/mint/ids",
    "JUP_TOKEN_LIST": "https://tokens.jup.ag/tokens?tags=lst,community",
    # pool APIs
    "POOL_LIST": "/pools/info/list",
    "POOL_SEARCH_BY_ID": "/pools/info/ids",
    "POOL_SEARCH_MINT": "/pools/info/mint",
    "POOL_SEARCH_LP": "/pools/info/lps",
    "POOL_KEY_BY_ID": "/pools/key/ids",
    "POOL_LIQUIDITY_LINE": "/pools/line/liquidity",
    "POOL_POSITION_LINE": "/pools/line/position",
    # farms (exposed for completeness)
    "FARM_INFO": "/farms/info/ids",
    "FARM_LP_INFO": "/farms/info/lp",
    "FARM_KEYS": "/farms/key/ids",
    # misc
    "PRIORITY_FEE": "/main/auto-fee",
    "CHAIN_TIME": "/main/chain-time",
}

# HTTP defaults
DEFAULT_TIMEOUT_SEC = 15
DEFAULT_RETRY = 3
