"""
Raydium / Solana constants (mainnet).

Sources (Raydium official & SPL docs):
- CLMM Program ID: CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK
- Token Program (SPL): TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA
- Token-2022 Program: TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb
- Raydium API base: https://api-v3.raydium.io
"""

# --- Their canonical program IDs (public) ---
CLMM_PROGRAM_ID = "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK"
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"

# --- Their API base (public API v3) ---
RAYDIUM_API_BASE = "https://api-v3.raydium.io"

# Owner APIs exposed in the TS SDK URL config (we may use later)
RAYDIUM_OWNER_API_BASE = "https://owner-v1.raydium.io"

# --- Sonic defaults ---
# Reads from env RPC_URL if present; can be overridden per call.
DEFAULT_TIMEOUT = 15.0
