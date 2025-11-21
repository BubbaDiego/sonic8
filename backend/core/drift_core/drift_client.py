from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional

from .drift_config import DriftConfig

logger = logging.getLogger(__name__)

try:
    from solana.rpc.async_api import AsyncClient
    from solana.publickey import PublicKey
    from anchorpy import Provider, Wallet
    from driftpy.drift_client import DriftClient as _DriftClient
    from driftpy.constants.config import configs as drift_configs

    DRIFTPY_AVAILABLE: bool = True
except Exception:  # noqa: BLE001 - we want to catch any import-time issues here
    AsyncClient = Any  # type: ignore[assignment]
    PublicKey = Any  # type: ignore[assignment]
    Provider = Any  # type: ignore[assignment]
    Wallet = Any  # type: ignore[assignment]
    _DriftClient = Any  # type: ignore[assignment]
    drift_configs = {}
    DRIFTPY_AVAILABLE = False


@dataclass
class DriftClientWrapper:
    """
    Thin wrapper around driftpy.DriftClient.

    This class centralizes all communication with Drift so that the rest
    of Sonic never needs to import driftpy directly.

    The initial implementation is intentionally stubbed; a follow-up pass
    will wire up actual RPC connections and queries.
    """

    config: DriftConfig
    cluster: str = "mainnet"
    rpc_client: Optional[AsyncClient] = field(default=None, init=False)
    wallet: Optional[Wallet] = field(default=None, init=False)
    provider: Optional[Provider] = field(default=None, init=False)
    drift_client: Optional[_DriftClient] = field(default=None, init=False)
    connected: bool = field(default=False, init=False)

    async def connect(self) -> None:
        """
        Initialize RPC client, wallet, provider and Drift client.

        This method should be awaited once on startup by whoever owns the
        DriftClientWrapper (e.g. DriftCore).

        NOTE: This is a stub for now and will be implemented in a follow-up
        pass once the structure is stable.
        """
        if not DRIFTPY_AVAILABLE:
            raise RuntimeError(
                "driftpy (and its Solana/Anchor dependencies) are not installed. "
                "Install driftpy and required packages before using DriftCore."
            )

        logger.debug("DriftClientWrapper.connect() called but not yet implemented.")
        raise NotImplementedError("DriftClientWrapper.connect is not implemented yet.")

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
            Optional base58 owner address; if omitted, use the configured wallet.

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

        This is intentionally high-level; DriftCore will translate Sonic-level
        intents into these parameters.

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
