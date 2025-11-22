from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional

from .drift_config import DriftConfig

logger = logging.getLogger(__name__)

# DriftPy + Solana imports are optional; we detect availability.
try:
    from solana.rpc.async_api import AsyncClient
    from anchorpy import Provider, Wallet
    from driftpy.drift_client import DriftClient as _DriftClient
    from driftpy.constants.config import configs as drift_configs

    DRIFTPY_AVAILABLE: bool = True
except Exception:  # noqa: BLE001
    AsyncClient = Any  # type: ignore[assignment]
    Provider = Any  # type: ignore[assignment]
    Wallet = Any  # type: ignore[assignment]
    _DriftClient = Any  # type: ignore[assignment]
    drift_configs = {}
    DRIFTPY_AVAILABLE = False

# Import the existing signer utilities (solder Keypair + mnemonic support)
try:
    from backend.services.signer_loader import load_signer
except Exception as e:  # pragma: no cover
    load_signer = None  # type: ignore[assignment]
    logger.warning("backend.services.signer_loader not available: %s", e)


@dataclass
class DriftClientWrapper:
    """
    Thin wrapper around DriftPy + Solana RPC.

    This class centralizes all communication with Drift so that the rest
    of Sonic never needs to import driftpy directly.

    NOTE: For now, only .connect() is implemented. The higher-level
    methods (get_markets, get_open_positions, place_perp_order) are
    stubbed and will be wired in a follow-up pass.
    """

    config: DriftConfig
    cluster: str = "mainnet"

    rpc_client: Optional[AsyncClient] = field(default=None, init=False)
    provider: Optional[Provider] = field(default=None, init=False)
    drift_client: Optional[_DriftClient] = field(default=None, init=False)

    connected: bool = field(default=False, init=False)
    owner_pubkey: Optional[str] = field(default=None, init=False)

    async def connect(self) -> None:
        """
        Initialize RPC client and attempt to load the signer via signer_loader.

        Behavior:
        - Uses signer_loader.load_signer() which resolves signer.txt (or
          SONIC_SIGNER_PATH) and supports:
            * id.json arrays
            * base64 blobs
            * key=value text with mnemonic=... [, passphrase=...]
            * plain 12–24 word mnemonics
        - Opens an AsyncClient against config.rpc_url.
        - If driftpy is available, prepares a Provider using Anchor's Wallet.
          (We intentionally defer constructing DriftClient until we wire
          its usage in follow-up passes.)
        """
        if self.connected:
            return

        if load_signer is None:
            raise RuntimeError(
                "backend.services.signer_loader.load_signer is not available; "
                "cannot initialize DriftClientWrapper. Ensure sonic6/sonic8 services are installed."
            )

        # 1) Load signer using the canonical signer_loader
        try:
            kp = load_signer()  # solders.keypair.Keypair from signer.txt
        except Exception as e:
            logger.error("Failed to load signer via signer_loader: %s", e)
            raise

        self.owner_pubkey = str(kp.pubkey())
        logger.info("DriftClientWrapper using owner pubkey: %s", self.owner_pubkey)

        # 2) Create RPC client
        logger.info("Connecting to Solana RPC for Drift: %s", self.config.rpc_url)
        self.rpc_client = AsyncClient(self.config.rpc_url, commitment=self.config.commitment)

        # 3) Optionally prepare an Anchor-style Provider if DriftPy is installed
        if DRIFTPY_AVAILABLE:
            try:
                wallet = Wallet(kp)  # AnchorPy wallet accepts solders Keypair
                self.provider = Provider(self.rpc_client, wallet)
                # NOTE: we deliberately do NOT construct DriftClient yet.
                # Once we start using drift_client, we will pick the right
                # config from drift_configs[self.cluster] and call its ctor.
                logger.info("DriftPy detected; provider prepared (cluster=%s).", self.cluster)
            except Exception as e:
                logger.error("Failed to prepare DriftPy Provider: %s", e)
                # We still consider ourselves "connected" for RPC-only flows.

        self.connected = True

    async def close(self) -> None:
        """
        Close underlying RPC client, if any.
        """
        if self.rpc_client is not None:
            await self.rpc_client.close()
        self.connected = False

    async def get_markets(self) -> List[dict]:
        """
        Fetch and return a list of Drift perp markets as plain dicts.

        Returns
        -------
        List[dict]
            A list of normalized market records suitable for persistence.

        NOTE: Stub implementation for now.
        """
        logger.debug("DriftClientWrapper.get_markets() called.")
        raise NotImplementedError("DriftClientWrapper.get_markets is not implemented yet.")

    async def get_open_positions(self, owner: Optional[str] = None) -> List[dict]:
        """
        Fetch open perp positions for the configured wallet or for a specific owner.

        Parameters
        ----------
        owner : Optional[str]
            Optional base58 owner address; if omitted, use self.owner_pubkey.

        Returns
        -------
        List[dict]
            Position records as plain dicts.

        NOTE: Stub implementation for now.
        """
        logger.debug("DriftClientWrapper.get_open_positions(owner=%s) called.", owner)
        raise NotImplementedError(
            "DriftClientWrapper.get_open_positions is not implemented yet."
        )

    async def place_perp_order(
        self,
        symbol: str,
        size_usd: float,
        side: str,
        reduce_only: bool = False,
        client_id: Optional[int] = None,
    ) -> str:
        """
        Place a perp order on Drift.

        Parameters
        ----------
        symbol :
            Market symbol such as 'SOL-PERP'.
        size_usd :
            Notional size of the order in USD.
        side :
            'long' or 'short'.
        reduce_only :
            If True, do not increase net exposure; only reduce.
        client_id :
            Optional client-order ID for idempotency and tracking.

        Returns
        -------
        str
            The transaction signature (base58) for the submitted order.

        NOTE: Stub implementation for now.
        """
        logger.debug(
            "DriftClientWrapper.place_perp_order(symbol=%s, size_usd=%s, side=%s, "
            "reduce_only=%s, client_id=%s)",
            symbol,
            size_usd,
            side,
            reduce_only,
            client_id,
        )
        raise NotImplementedError(
            "DriftClientWrapper.place_perp_order is not implemented yet."
        )


__all__ = ["DriftClientWrapper", "DRIFTPY_AVAILABLE"]
