from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class DriftConfig:
    """
    Configuration for connecting to Drift and Solana RPC.

    This version is intentionally hard-coded to use the public Solana
    mainnet RPC endpoint to avoid all the Helius/env-variable drama.

    If/when you want to switch back to a custom RPC, we can extend this
    again, but for now we keep it dead simple and reliable.
    """

    # Hard-coded RPC URL: public Solana mainnet
    rpc_url: str = "https://api.mainnet-beta.solana.com"

    # We are not using WALLET_SECRET_BASE64 for Drift; signer_loader
    # handles signer.txt / mnemonics. These fields are kept for
    # compatibility with existing code, but are effectively unused.
    wallet_secret_base64: Optional[str] = None
    commitment: str = "confirmed"
    jito_tip_lamports: int = 0

    @classmethod
    def from_env(cls) -> "DriftConfig":
        """
        Return a DriftConfig with a fixed RPC URL.

        Ignoring environment variables is intentional here to avoid
        accidentally picking up a broken Helius URL from the OS env.
        """
        return cls()


def get_drift_config() -> DriftConfig:
    """
    Convenience helper for callers that just want a config instance.
    """
    return DriftConfig.from_env()
