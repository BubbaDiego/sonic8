from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional

from .drift_config import DriftConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DriftPy + Solana imports
# ---------------------------------------------------------------------------

DRIFTPY_AVAILABLE: bool = False
DRIFTPY_IMPORT_ERROR: Optional[str] = None

try:
    from solana.rpc.async_api import AsyncClient
    from anchorpy import Provider, Wallet
    from driftpy.drift_client import DriftClient as _DriftClient
    from driftpy.constants.config import configs as drift_configs
    from driftpy.constants.numeric_constants import BASE_PRECISION
    from driftpy.types import PositionDirection

    DRIFTPY_AVAILABLE = True
    DRIFTPY_IMPORT_ERROR = None
except Exception as e:  # noqa: BLE001
    # Degrade gracefully but remember why imports failed.
    AsyncClient = Any  # type: ignore[assignment]
    Provider = Any  # type: ignore[assignment]
    Wallet = Any  # type: ignore[assignment]
    _DriftClient = Any  # type: ignore[assignment]
    drift_configs = {}
    BASE_PRECISION = 1
    PositionDirection = Any  # type: ignore[assignment]

    DRIFTPY_AVAILABLE = False
    DRIFTPY_IMPORT_ERROR = repr(e)
    logger.warning("DriftPy imports failed; DRIFTPY_AVAILABLE=False: %s", DRIFTPY_IMPORT_ERROR)

# Existing signer utilities (signer.txt + mnemonic support)
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

    For this pass:
    - .connect() is fully implemented.
    - .place_perp_order() opens a simple perp position via DriftPy.
    - .get_markets() / .get_open_positions() remain stubs.
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
        - Uses signer_loader.load_signer() to resolve signer.txt (or SONIC_SIGNER_PATH).
        - Opens an AsyncClient against config.rpc_url.
        - If DriftPy is available:
            * Builds Provider(wallet, connection).
            * Builds DriftClient.from_config(configs[cluster], provider).
            * Ensures sub-account 0 exists and is subscribed.

        This method is idempotent; subsequent calls are no-ops.
        """
        if self.connected:
            return

        if load_signer is None:
            raise RuntimeError(
                "backend.services.signer_loader.load_signer is not available; "
                "cannot initialize DriftClientWrapper. Ensure services are installed."
            )

        # 1) Load signer using canonical signer_loader
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

        # 3) Prepare Provider + DriftClient if DriftPy is installed
        if DRIFTPY_AVAILABLE:
            try:
                wallet = Wallet(kp)
                self.provider = Provider(self.rpc_client, wallet)
                cfg = drift_configs.get(self.cluster)
                if cfg is None:
                    raise KeyError(f"No Drift config for cluster '{self.cluster}'")

                self.drift_client = _DriftClient.from_config(cfg, self.provider)

                # Ensure a user account exists & subscribe it
                try:
                    # Try to attach the default sub-account (0)
                    await self.drift_client.add_user(0)
                except Exception as add_err:
                    logger.warning(
                        "add_user(0) failed; attempting initialize_user(): %s", add_err
                    )
                    # If user account doesn't exist yet, initialize and retry
                    await self.drift_client.initialize_user()
                    await self.drift_client.add_user(0)

                await self.drift_client.subscribe()
                logger.info("Drift client subscribed (cluster=%s).", self.cluster)

            except Exception as e:
                logger.error("Failed to prepare DriftPy client: %s", e)
                # We still consider ourselves "connected" for RPC-only flows,
                # but trading will fail with a clear error.

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

        NOTE: Stub implementation for now.
        """
        logger.debug("DriftClientWrapper.get_markets() called.")
        raise NotImplementedError("DriftClientWrapper.get_markets is not implemented yet.")

    async def get_open_positions(self, owner: Optional[str] = None) -> List[dict]:
        """
        Fetch open perp positions for the configured wallet or for a specific owner.

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

        IMPORTANT:
        - For now, `size_usd` is treated as *base size* (e.g. 0.1 SOL), not USD notional.
          The Drift Console text is updated to reflect this.
        - We rely on DriftClient.get_market_index_and_type(name) to resolve the market index
          instead of hard-coding indices. Example: "SOL-PERP" -> (0, MarketType.Perp()).

        Parameters
        ----------
        symbol :
            Market symbol such as 'SOL-PERP'.
        size_usd :
            Base size in units (e.g. 0.1 SOL), will be converted to BASE_PRECISION.
        side :
            'long' or 'short'.
        reduce_only :
            Currently unused; reserved for future use.
        client_id :
            Optional client-order ID for idempotency and tracking.

        Returns
        -------
        str
            The transaction signature (base58) for the submitted order.
        """
        if not DRIFTPY_AVAILABLE:
            raise RuntimeError(
                "DriftPy is not installed in this environment. "
                "Install it with `pip install driftpy` to place Drift orders."
            )

        # Ensure connection + Drift client ready
        await self.connect()
        if self.drift_client is None:
            raise RuntimeError("Drift client is not initialized; cannot place orders.")

        # Resolve market index from symbol using Drift's own helper
        result = self.drift_client.get_market_index_and_type(symbol)
        if result is None:
            raise ValueError(f"Unknown Drift market symbol: {symbol}")
        market_index, market_type = result  # we assume symbol is for a perp market

        # Convert base size to on-chain units
        try:
            base_size = float(size_usd)
        except Exception as e:
            raise ValueError(f"Invalid size value: {size_usd}") from e

        amount = int(base_size * BASE_PRECISION)
        if amount <= 0:
            raise ValueError(f"Order size must be positive; got {base_size}.")

        # Direction mapping
        side_norm = side.strip().lower()
        if side_norm not in ("long", "short"):
            raise ValueError(f"Unsupported side: {side}")
        direction = PositionDirection.LONG() if side_norm == "long" else PositionDirection.SHORT()

        logger.info(
            "Placing Drift perp order: symbol=%s market_index=%s side=%s base_size=%s amount=%s",
            symbol,
            market_index,
            side_norm,
            base_size,
            amount,
        )

        # Use the simple open_position helper as documented in DriftPy examples.
        sig = await self.drift_client.open_position(
            direction=direction,
            amount=amount,
            market_index=market_index,
        )

        logger.info("Drift perp order submitted; signature=%s", sig)
        return sig


__all__ = ["DriftClientWrapper", "DRIFTPY_AVAILABLE", "DRIFTPY_IMPORT_ERROR"]
