from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from backend.data.data_locker import DataLocker

from .drift_core import DriftCore

logger = logging.getLogger(__name__)


class DriftCoreService:
    """
    Thin service/facade for DriftCore.

    This is the preferred entrypoint for HTTP routes, monitors, and consoles.
    """

    def __init__(self, dl: DataLocker, core: Optional[DriftCore] = None) -> None:
        self._dl = dl
        self._core = core or DriftCore(dl)

    @property
    def core(self) -> DriftCore:
        return self._core

    async def health(self) -> Dict[str, Any]:
        """
        Return a health payload suitable for an API route.
        """
        return await self._core.health_check()

    async def refresh_positions_and_snapshot(self) -> Dict[str, Any]:
        """
        Refresh Drift positions and return a summary payload.

        In a follow-up implementation, this will also drive portfolio snapshots
        and any hedging flows that depend on up-to-date positions.
        """
        logger.info("DriftCoreService.refresh_positions_and_snapshot() called.")
        await self._core.sync_all_positions()
        # TODO: integrate with existing portfolio snapshot & session APIs.
        return {"status": "ok", "source": "drift", "message": "Positions sync triggered."}

    async def open_simple_long(self, symbol: str, size_usd: float) -> Dict[str, Any]:
        """
        Open a basic long perp position on Drift and return the tx signature.

        This method is intentionally opinionated and is meant to support
        CLI/frontend flows that do not need full control over every parameter.
        """
        logger.info(
            "DriftCoreService.open_simple_long(symbol=%s, size_usd=%s)", symbol, size_usd
        )
        sig = await self._core.open_perp_order(
            symbol=symbol,
            size_usd=size_usd,
            side="long",
            reduce_only=False,
        )
        return {
            "status": "ok",
            "symbol": symbol,
            "size_usd": size_usd,
            "sig": sig,
        }
