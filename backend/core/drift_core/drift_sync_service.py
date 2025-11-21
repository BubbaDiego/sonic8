from __future__ import annotations

import logging

from backend.data.data_locker import DataLocker

from .drift_client import DriftClientWrapper
from .drift_store import DriftStore

logger = logging.getLogger(__name__)


class DriftSyncService:
    """
    Orchestrates synchronization of markets and positions from Drift into Sonic.

    This class should remain side-effect-free beyond persistence via DataLocker.
    """

    def __init__(self, dl: DataLocker, client: DriftClientWrapper, store: DriftStore) -> None:
        self._dl = dl
        self._client = client
        self._store = store

    async def sync_markets(self) -> None:
        """
        Fetch markets from Drift and persist them (once a concrete storage
        strategy is in place).

        NOTE: Stub implementation for now.
        """
        logger.info("DriftSyncService.sync_markets() called.")
        # TODO: fetch via self._client.get_markets() and persist via DriftStore.
        raise NotImplementedError("DriftSyncService.sync_markets is not implemented yet.")

    async def sync_positions_for_owner(self, owner: str) -> None:
        """
        Fetch open positions for a given owner and persist them via DriftStore.

        NOTE: Stub implementation for now.
        """
        logger.info("DriftSyncService.sync_positions_for_owner(owner=%s) called.", owner)
        # TODO:
        # positions = await self._client.get_open_positions(owner=owner)
        # self._store.upsert_positions(owner, positions)
        raise NotImplementedError(
            "DriftSyncService.sync_positions_for_owner is not implemented yet."
        )

    async def sync_all_positions(self) -> None:
        """
        Convenience method to sync positions for the primary configured wallet.

        Ownership resolution (wallet name vs raw pubkey) will be defined by
        DriftCore in a later pass.

        NOTE: Stub implementation for now.
        """
        logger.info("DriftSyncService.sync_all_positions() called.")
        raise NotImplementedError(
            "DriftSyncService.sync_all_positions is not implemented yet."
        )
