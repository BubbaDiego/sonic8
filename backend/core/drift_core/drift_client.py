from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from solana.exceptions import SolanaRpcException

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
    from driftpy.constants.numeric_constants import BASE_PRECISION, QUOTE_PRECISION
    from driftpy.types import (
        PositionDirection,
        OrderParams,
        OrderType,
        MarketType,
    )

    DRIFTPY_AVAILABLE = True
    DRIFTPY_IMPORT_ERROR = None
except Exception as e:  # noqa: BLE001
    AsyncClient = Any  # type: ignore[assignment]
    Provider = Any  # type: ignore[assignment]
    Wallet = Any  # type: ignore[assignment]
    _DriftClient = Any  # type: ignore[assignment]
    BASE_PRECISION = 1
    QUOTE_PRECISION = 1
    PositionDirection = Any  # type: ignore[assignment]
    OrderParams = Any  # type: ignore[assignment]
    OrderType = Any  # type: ignore[assignment]
    MarketType = Any  # type: ignore[assignment]

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
    """

    config: DriftConfig
    cluster: str = "mainnet"

    rpc_client: Optional[AsyncClient] = field(default=None, init=False)
    provider: Optional[Provider] = field(default=None, init=False)
    drift_client: Optional[_DriftClient] = field(default=None, init=False)

    connected: bool = field(default=False, init=False)
    owner_pubkey: Optional[str] = field(default=None, init=False)

    # ------------------------------------------------------------------
    # Connection / init
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """
        Initialize RPC client and Drift client.

        Steps:
        - Load signer using signer_loader (signer.txt, mnemonic=..., etc.).
        - Create AsyncClient with configured RPC URL.
        - Create Provider(wallet, connection).
        - Create DriftClient(connection, wallet, env).
        - Subscribe accounts.
        - Ensure sub-account 0 exists and is registered.
        """
        if self.connected and self.drift_client is not None:
            return

        if not DRIFTPY_AVAILABLE:
            raise RuntimeError(
                f"DriftPy is not available in this environment: {DRIFTPY_IMPORT_ERROR}"
            )

        if load_signer is None:
            raise RuntimeError(
                "backend.services.signer_loader.load_signer is not available; "
                "cannot initialize DriftClientWrapper."
            )

        # 1) Load signer
        try:
            kp = load_signer()  # solders.keypair.Keypair from signer.txt
        except Exception as e:
            logger.error("Failed to load signer via signer_loader: %s", e)
            raise RuntimeError(f"Failed to load signer: {e!r}") from e

        self.owner_pubkey = str(kp.pubkey())
        logger.info("DriftClientWrapper using owner pubkey: %s", self.owner_pubkey)

        # 2) RPC client
        logger.info("Connecting to Solana RPC for Drift: %s", self.config.rpc_url)
        self.rpc_client = AsyncClient(self.config.rpc_url, commitment=self.config.commitment)

        # 3) Provider + DriftClient
        try:
            wallet = Wallet(kp)
            self.provider = Provider(self.rpc_client, wallet)

            env = self.cluster or "mainnet"
            self.drift_client = _DriftClient(
                connection=self.rpc_client,
                wallet=wallet,
                env=env,
            )

            # Subscribe BEFORE touching users
            logger.info("Subscribing Drift client (env=%s)...", env)
            await self.drift_client.subscribe()

            # Try to attach sub-account 0; if that fails, initialize the user
            try:
                await self.drift_client.add_user(0)
                logger.info("Drift sub-account 0 registered.")
            except Exception as add_err:
                logger.warning(
                    "add_user(0) failed; attempting initialize_user(): %s", add_err
                )
                await self.drift_client.initialize_user()
                # Re-subscribe to see new accounts
                await self.drift_client.subscribe()
                await self.drift_client.add_user(0)
                logger.info("Drift user initialized and sub-account 0 registered.")

            logger.info("Drift client ready (env=%s).", env)

        except Exception as e:
            logger.error("Failed to prepare DriftPy client: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to prepare DriftPy client: {e!r}") from e

        self.connected = True

    async def close(self) -> None:
        """
        Close underlying RPC client, if any.
        """
        if self.rpc_client is not None:
            await self.rpc_client.close()
        self.connected = False

    # ------------------------------------------------------------------
    # Balance / positions
    # ------------------------------------------------------------------

    async def get_balance_summary(self) -> Dict[str, Any]:
        """
        Return a summary of the user's Drift collateral metrics.

        Uses DriftClient.get_user() and DriftUser methods:

        - get_total_collateral()
        - get_free_collateral()

        Values are in QUOTE_PRECISION units; we also return UI-normalized floats.
        """
        try:
            await self.connect()
        except Exception as e:
            raise RuntimeError(f"Drift connection failed: {e!r}") from e

        if self.drift_client is None:
            raise RuntimeError("Drift client is not initialized; cannot fetch balances.")

        try:
            drift_user = self.drift_client.get_user()
            total_collateral = drift_user.get_total_collateral()
            free_collateral = drift_user.get_free_collateral()
        except Exception as e:
            logger.error("Error fetching Drift balances: %s", e, exc_info=True)
            raise RuntimeError(f"Drift balance fetch failed: {e!r}") from e

        total_ui = float(total_collateral) / float(QUOTE_PRECISION)
        free_ui = float(free_collateral) / float(QUOTE_PRECISION)

        return {
            "owner": self.owner_pubkey,
            "total_collateral_quote": int(total_collateral),
            "free_collateral_quote": int(free_collateral),
            "total_collateral_ui": total_ui,
            "free_collateral_ui": free_ui,
            "quote_precision": int(QUOTE_PRECISION),
        }

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

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

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

        `size_usd` is treated as base size (e.g. 0.1 SOL) and converted to
        perp precision using DriftClient.convert_to_perp_precision().
        """
        if not DRIFTPY_AVAILABLE:
            raise RuntimeError(
                f"DriftPy is not available in this environment: {DRIFTPY_IMPORT_ERROR}"
            )

        await self.connect()
        if self.drift_client is None:
            raise RuntimeError("Drift client is not initialized; cannot place orders.")

        # Resolve market index and type from symbol using Drift helper
        result = self.drift_client.get_market_index_and_type(symbol)
        if result is None:
            raise ValueError(f"Unknown Drift market symbol: {symbol}")
        market_index, market_type = result  # e.g. (0, MarketType.Perp())

        # Convert base size to perp precision
        try:
            base_size = float(size_usd)
        except Exception as e:
            raise ValueError(f"Invalid size value: {size_usd}") from e

        if base_size <= 0:
            raise ValueError(f"Order size must be positive; got {base_size}.")

        amount = self.drift_client.convert_to_perp_precision(base_size)

        # Direction mapping (tolerate different driftpy variants)
        side_norm = side.strip().lower()
        if side_norm not in ("long", "short"):
            raise ValueError(f"Unsupported side: {side}")

        def _resolve_direction(attr_candidates):
            for attr in attr_candidates:
                if hasattr(PositionDirection, attr):
                    val = getattr(PositionDirection, attr)
                    return val() if callable(val) else val
            raise RuntimeError(
                f"PositionDirection does not expose any of {attr_candidates} "
                f"for side='{side_norm}'."
            )

        if side_norm == "long":
            direction = _resolve_direction(("LONG", "Long"))
        else:
            direction = _resolve_direction(("SHORT", "Short"))

        logger.info(
            "Placing Drift perp order: symbol=%s market_index=%s side=%s base_size=%s amount=%s market_type=%s",
            symbol,
            market_index,
            side_norm,
            base_size,
            amount,
            market_type,
        )

        order_params = OrderParams(
            order_type=OrderType.Market(),
            market_index=market_index,
            market_type=market_type,
            direction=direction,
            base_asset_amount=amount,
        )

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                sig = await self.drift_client.place_perp_order(order_params)
                logger.info("Drift perp order submitted; signature=%s", sig)
                return sig
            except SolanaRpcException as e:
                msg = repr(e)
                if "429" in msg and attempt < max_attempts:
                    delay = 1.0 * (2 ** (attempt - 1))
                    logger.warning(
                        "Solana RPC 429 Too Many Requests when placing Drift order; "
                        "attempt %s/%s, sleeping %.1fs",
                        attempt,
                        max_attempts,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    continue

                logger.error(
                    "SolanaRpcException when placing Drift order (attempt %s/%s): %s",
                    attempt,
                    max_attempts,
                    msg,
                )
                raise
            except Exception as e:
                logger.error("Unexpected error placing Drift order: %s", repr(e), exc_info=True)
                raise


__all__ = ["DriftClientWrapper", "DRIFTPY_AVAILABLE", "DRIFTPY_IMPORT_ERROR"]
