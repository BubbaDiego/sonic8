from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional


@dataclass
class DriftConfig:
    """
    Configuration for connecting to Drift and Solana RPC.

    This is intentionally minimal for now; additional tuning parameters
    (like priority fees, Jito integration, etc.) can be added later as
    needed.
    """

    rpc_url: str
    wallet_secret_base64: Optional[str]
    commitment: str = "confirmed"
    jito_tip_lamports: int = 0

    @classmethod
    def from_env(cls) -> "DriftConfig":
        """
        Load Drift configuration from environment variables.

        Precedence:
        - DRIFT_RPC_URL      (if set)
        - RPC_URL            (global Solana RPC)
        - hardcoded fallback (api.mainnet-beta.solana.com)

        Wallet secret:
        - DRIFT_WALLET_SECRET_BASE64
        - WALLET_SECRET_BASE64
        """
        rpc_url = (
            os.getenv("DRIFT_RPC_URL")
            or os.getenv("RPC_URL")
            or "https://api.mainnet-beta.solana.com"
        )

        wallet_secret_base64 = (
            os.getenv("DRIFT_WALLET_SECRET_BASE64")
            or os.getenv("WALLET_SECRET_BASE64")
        )

        commitment = os.getenv("DRIFT_COMMITMENT", "confirmed")

        jito_tip_str = os.getenv(
            "DRIFT_JITO_TIP_LAMPORTS",
            os.getenv("JITO_TIP_LAMPORTS", "0"),
        )
        try:
            jito_tip_lamports = int(jito_tip_str)
        except ValueError:
            jito_tip_lamports = 0

        return cls(
            rpc_url=rpc_url,
            wallet_secret_base64=wallet_secret_base64,
            commitment=commitment,
            jito_tip_lamports=jito_tip_lamports,
        )


def get_drift_config() -> DriftConfig:
    """
    Convenience helper for callers that just want a config instance.
    """
    return DriftConfig.from_env()
