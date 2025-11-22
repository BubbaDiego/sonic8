from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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
    from driftpy.constants.numeric_constants import BASE_PRECISION, QUOTE_PRECISION
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
    QUOTE_PRECISION = 1
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
            * Builds DriftClient(connection, wallet, env=cluster).
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

                # Directly construct DriftClient via its __init__ as documented,
                # instead of using from_config (which is not present in your version).
                # Env can be "mainnet" or "devnet"; default DriftEnv is "mainnet".
                env = self.cluster or "mainnet"

                self.drift_client = _DriftClient(
                    connection=self.rpc_client,
                    wallet=wallet,
                    env=env,
                    # Use default account_subscription / markets; we can refine later
                    # if you want demo-mode or limited markets.
                )

                # Ensure there is a user account and subscribe
                try:
                    await self.drift_client.add_user(0)
                except Exception as add_err:
                    logger.warning(
                        "add_user(0) failed; attempting initialize_user(): %s", add_err
                    )
                    await self.drift_client.initialize_user()
                    await self.drift_client.add_user(0)

                await self.drift_client.subscribe()
                logger.info("Drift client subscribed (env=%s).", env)

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

        # Direction mapping (support multiple driftpy variants)
        side_norm = side.strip().lower()
        if side_norm not in ("long", "short"):
            raise ValueError(f"Unsupported side: {side}")

        def _resolve_direction(attr_candidates):
            for attr in attr_candidates:
                if hasattr(PositionDirection, attr):
                    val = getattr(PositionDirection, attr)
                    # Some versions expose a callable (Long()), others a constant (LONG)
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

    async def get_balance_summary(self) -> Dict[str, Any]:
        """
        Return a summary of the user's Drift collateral metrics.

        Uses DriftClient.get_user() (which returns a DriftUser) and reads:
        - total_collateral: net asset value including PnL, in QUOTE_PRECISION units
        - free_collateral: collateral available for new positions, in QUOTE_PRECISION

        These correspond to Drift's standard margin metrics.
        """
        if not DRIFTPY_AVAILABLE:
            raise RuntimeError(
                f"DriftPy is not available in this environment: {DRIFTPY_IMPORT_ERROR}"
            )

        await self.connect()
        if self.drift_client is None:
            raise RuntimeError("Drift client is not initialized; cannot fetch balances.")

        # Ensure we have a user object. connect() already did add_user(0),
        # so get_user() should give us a DriftUser bound to the active sub-account.
        drift_user = self.drift_client.get_user()

        # These methods are synchronous and operate on the subscribed accounts.
        total_collateral = drift_user.get_total_collateral()
        free_collateral = drift_user.get_free_collateral()

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


__all__ = ["DriftClientWrapper", "DRIFTPY_AVAILABLE", "DRIFTPY_IMPORT_ERROR"]
