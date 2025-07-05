"""CyclonePositionService – thin facade for Jupiter sync & enrichment.

Auto‑imports heavy PositionCore helpers on demand so the service is safe to
import inside FastAPI background tasks.
"""
from data.data_locker import DataLocker
from core.core_imports import log
import asyncio

class CyclonePositionService:
    def __init__(self, dl: DataLocker):
        self.dl = dl
        self.loop = asyncio.get_event_loop()

    # ------------------------------------------------------------------ #
    # Public helpers wired to API & console                              #
    # ------------------------------------------------------------------ #
    def update_positions_from_jupiter(self):
        from backend.core.positions_core.position_sync_service import (
            PositionSyncService,
        )
        log.info("🚀 Running Jupiter sync", source="CyclonePosition")
        PositionSyncService(self.dl).run_full_jupiter_sync(source="api")

    async def enrich_positions(self):
        from backend.core.positions_core.position_core import PositionCore
        log.info("🧠 Enriching positions", source="CyclonePosition")
        await PositionCore(self.dl).enrich_positions()

    # ------------------------------------------------------------------ #
    # Debug helpers                                                      #
    # ------------------------------------------------------------------ #
    def view_positions(self):
        rows = self.dl.positions.get_all_positions()
        for r in rows:
            print(r)
