"""CyclonePositionService – thin facade for Jupiter sync & enrichment.

Auto‑imports heavy PositionCore helpers on demand so the service is safe to
import inside FastAPI background tasks.
"""
from backend.data.data_locker import DataLocker
from backend.core.logging import log
import asyncio

class CyclonePositionService:
    def __init__(self, dl: DataLocker):
        self.dl = dl
        self.loop = asyncio.get_event_loop()

    def _count_positions(self) -> int:
        """Best-effort count of positions available via manager or DB."""
        mgr = getattr(self.dl, "positions", None)
        if mgr:
            for name in ("get_positions", "get_all_positions", "list", "get_all"):
                fn = getattr(mgr, name, None)
                if callable(fn):
                    try:
                        rows = fn()
                    except TypeError:
                        try:
                            rows = fn(None)
                        except Exception:
                            continue
                    except Exception:
                        continue
                    if isinstance(rows, list):
                        return len(rows)
            try:
                rows = mgr.positions if isinstance(getattr(mgr, "positions", None), list) else None
                if rows is not None:
                    return len(rows)
            except Exception:
                pass
        try:
            cur = self.dl.db.get_cursor()
            cur.execute("SELECT COUNT(*) FROM positions")
            row = cur.fetchone()
            if row and row[0] is not None:
                return int(row[0])
        except Exception:
            pass
        return 0

    # ------------------------------------------------------------------ #
    # Public helpers wired to API & console                              #
    # ------------------------------------------------------------------ #
    def update_positions_from_jupiter(self):
        from backend.core.positions_core.position_sync_service import (
            PositionSyncService,
        )
        log.info("🚀 Running Jupiter sync", source="CyclonePosition")
        PositionSyncService(self.dl).run_full_jupiter_sync(source="api")

    @classmethod
    def run_full(cls, dl: DataLocker, source: str = "sonic") -> int:
        """Run the full Jupiter sync and return the resulting position count."""

        from backend.core.positions_core.position_sync_service import PositionSyncService

        service = cls(dl)
        PositionSyncService(dl).run_full_jupiter_sync(source=source)
        return service._count_positions()

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
