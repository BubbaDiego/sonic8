# dl_hedges.py
"""
Author: BubbaDiego
Module: DLHedgeManager
Description:
    Provides retrieval of hedge data from the database. This manager
    queries positions that have a ``hedge_buddy_id`` set and converts
    them into :class:`~data.models.Hedge` objects using
    :class:`~positions.hedge_manager.HedgeManager`.
"""

try:
    from positions.hedge_manager import HedgeManager
except ModuleNotFoundError:  # pragma: no cover - fallback to new path
    from core.positions_core.hedge_manager import HedgeManager
from core.core_imports import log


class DLHedgeManager:
    def __init__(self, db):
        self.db = db
        log.debug("DLHedgeManager initialized.", source="DLHedgeManager")

    def get_hedges(self) -> list:
        """Return a list of :class:`Hedge` objects from existing positions."""
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable while fetching hedges", source="DLHedgeManager")
                return []
            cursor.execute(
                "SELECT * FROM positions WHERE hedge_buddy_id IS NOT NULL"
            )
            rows = cursor.fetchall()
            positions = [dict(row) for row in rows]
            hedge_manager = HedgeManager(positions)
            hedges = hedge_manager.get_hedges()
            log.debug(f"Retrieved {len(hedges)} hedges", source="DLHedgeManager")
            return hedges
        except Exception as e:
            log.error(f"Failed to retrieve hedges: {e}", source="DLHedgeManager")
            return []

    def get_long_short_positions(self, hedge_id: str):
        cursor = self.db.get_cursor()
        if cursor is None:
            log.error("DB unavailable while fetching positions", source="DLHedgeManager")
            return None, None

        cursor.execute(
            "SELECT * FROM positions WHERE hedge_buddy_id = ?", (hedge_id,)
        )
        rows = cursor.fetchall()
        long_pos = short_pos = None
        for row in rows:
            pos = dict(row)
            if pos["position_type"].lower() == "long":
                long_pos = pos
            elif pos["position_type"].lower() == "short":
                short_pos = pos

        if not long_pos or not short_pos:
            log.warning(f"Incomplete hedge data for hedge_id {hedge_id}", source="DLHedgeManager")

        return long_pos, short_pos
