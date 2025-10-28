from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


def _as_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    v = value.strip().lower()
    return v in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class JupiterConfig:
    """Configuration container for Jupiter API interactions."""

    # Tier/feature flags
    tier: str = os.getenv("JUP_TIER", "lite")
    use_ultra: bool = _as_bool(os.getenv("JUP_USE_ULTRA", "1"), True)

    # Auth (Pro/Ultra may require this)
    api_key: Optional[str] = os.getenv("JUP_API_KEY")

    # Base URLs (override-able via env for safety)
    # NOTE: If Jupiter updates endpoints, set env vars and relaunch.
    ultra_base: str = os.getenv("JUP_ULTRA_BASE", "https://api.jup.ag/ultra")
    swap_base: str = os.getenv("JUP_SWAP_BASE", "https://api.jup.ag")
    trigger_base: str = os.getenv("JUP_TRIGGER_BASE", "https://api.jup.ag/trigger")

    # DB path (for audit log fallback when DataLocker is unavailable)
    mother_db_path: str = os.getenv("MOTHER_DB_PATH", "backend/mother.db")

    # Wallet discovery & derivation
    signer_path: Optional[str] = os.getenv("SIGNER_PATH")
    solana_derivation_path: str = os.getenv("SOLANA_DERIVATION_PATH", "m/44'/501'/0'/0'")
    solana_rpc_url: str = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")

    # Default mints (mainnet) — override with env if you prefer alternates.
    # WSOL & USDC are canonical; WETH/WBTC reflect Wormhole/Portal bridges.
    wsol_mint: str = os.getenv(
        "JUP_WSOLUMINT",
        "So11111111111111111111111111111111111111112",
    )
    usdc_mint: str = os.getenv(
        "JUP_USDCMINT",
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    )
    weth_mint: str = os.getenv(
        "JUP_WETHMINT",
        "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",
    )
    wbtc_mint: str = os.getenv(
        "JUP_WBTCMINT",
        "3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh",
    )

    # Legacy defaults used elsewhere (quote/order examples)
    default_input_mint: str = os.getenv("JUP_DEFAULT_INPUT_MINT", wsol_mint)
    default_output_mint: str = os.getenv("JUP_DEFAULT_OUTPUT_MINT", usdc_mint)


def get_config() -> JupiterConfig:
    """Return a ``JupiterConfig`` with environment defaults applied."""

    return JupiterConfig()
