from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from backend.data.data_locker import DataLocker

from .drift_config import DriftConfig
from .drift_client import DriftClientWrapper, DRIFTPY_AVAILABLE, DRIFTPY_IMPORT_ERROR
from .drift_store import DriftStore
from .drift_sync_service import DriftSyncService

logger = logging.getLogger(__name__)


class DriftCore:
    """
    High-level orchestrator for Drift interactions inside Sonic.

    This class composes DriftClientWrapper, DriftStore, and DriftSyncService and
    exposes a small, stable API for the rest of the system to use.
    """

    def __init__(
        self,
        dl: DataLocker,
        config: Optional[DriftConfig] = None,
        *,
        cluster: str = "mainnet",
    ) -> None:
        self._dl = dl
        self._config = config or DriftConfig.from_env()
        self._client = DriftClientWrapper(self._config, cluster=cluster)
        self._store = DriftStore(dl)
        self._sync = DriftSyncService(dl, self._client, self._store)

    @property
    def config(self) -> DriftConfig:
        return self._config

    @property
    def client(self) -> DriftClientWrapper:
        return self._client

    @property
    def store(self) -> DriftStore:
        return self._store

    @property
    def sync(self) -> DriftSyncService:
        return self._sync

    async def health_check(self) -> Dict[str, Any]:
        """
        Lightweight health probe for DriftCore.

        This method is safe to call from an HTTP route or monitor.

        It reports:
        - RPC URL being used.
        - DriftPy import availability.
        - Signer diagnostics from backend.services.signer_loader.diagnose_signer().
        """
        logger.info("DriftCore.health_check() called.")

        # Import here to avoid hard dependency if services package is missing.
        try:
            from backend.services.signer_loader import diagnose_signer  # type: ignore[import]
        except Exception as e:
            signer_status: Dict[str, Any] = {
                "ok": False,
                "error": f"signer_loader not available: {e}",
            }
        else:
            try:
                diag = diagnose_signer()
                signer_status = {
                    "ok": bool(diag.get("exists")),
                    "spec": diag.get("spec"),
                    "found": diag.get("found"),
                    "exists": diag.get("exists"),
                    "error": diag.get("error", ""),
                }
            except Exception as e:
                signer_status = {
                    "ok": False,
                    "error": f"diagnose_signer failed: {e}",
                }

        return {
            "rpc_url": self._config.rpc_url,
            "driftpy_available": DRIFTPY_AVAILABLE,
            "driftpy_error": DRIFTPY_IMPORT_ERROR,
            "signer": signer_status,
        }

    async def get_balance_summary(self) -> Dict[str, Any]:
        """
        High-level helper to fetch Drift balance metrics for the primary wallet.

        Returns a dict describing:
        - owner (pubkey)
        - total_collateral_quote / free_collateral_quote (raw ints)
        - total_collateral_ui / free_collateral_ui (USD-ish, QUOTE_PRECISION-normalized)
        """
        logger.info("DriftCore.get_balance_summary() called.")
        return await self._client.get_balance_summary()

    async def sync_all_positions(self) -> None:
        """
        Delegate to DriftSyncService to refresh positions for the primary owner.

        A later pass will define how the owner identity is derived (e.g. from
        the configured wallet or from a named Sonic wallet record).
        """
        logger.info("DriftCore.sync_all_positions() called.")
        await self._sync.sync_all_positions()

    async def open_perp_order(
        self,
        symbol: str,
        size_usd: float,
        side: str,
        *,
        reduce_only: bool = False,
    ) -> str:
        """
        High-level helper to open a perp order on Drift.

        NOTE: For now, `size_usd` is treated as base size (e.g. 0.1 SOL) and the
        console text has been updated accordingly.

        Parameters
        ----------
        symbol :
            Market symbol such as 'SOL-PERP'.
        size_usd :
            Base size in asset units (not USD notional).
        side :
            'long' or 'short'.
        reduce_only :
            Reserved for future use.

        Returns
        -------
        str
            Signature of the submitted transaction.
        """
        logger.info(
            "DriftCore.open_perp_order(symbol=%s, size_usd=%s, side=%s, reduce_only=%s)",
            symbol,
            size_usd,
            side,
            reduce_only,
        )
        return await self._client.place_perp_order(
            symbol=symbol,
            size_usd=size_usd,
            side=side,
            reduce_only=reduce_only,
        )
