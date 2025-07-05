import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from typing import List, Optional
from uuid import uuid4
from datetime import datetime

from backend.models.hedge import Hedge
from typing import TYPE_CHECKING

# Avoid circular dependency with :mod:`positions.hedge_manager` when this module
# is imported. HedgeManager is only needed inside methods, so defer the import
# until runtime or when type checking.
if TYPE_CHECKING:  # pragma: no cover - used for type hints only
    from backend.core.positions_core.hedge_manager import HedgeManager
from backend.core.core_imports import log

class HedgeCore:
    """High level orchestration for hedge operations"""
    def __init__(self, data_locker):
        self.dl = data_locker


    def update_hedges(self):
        """Build Hedge objects from current positions"""
        log.info("🔄 Updating hedges", source="HedgeCore")
        try:
            from backend.core.positions_core.hedge_manager import HedgeManager as _HedgeManager
            # Ensure hedge_buddy_id values are up-to-date
            _HedgeManager.find_hedges()
            raw_positions = [
                p.model_dump() if hasattr(p, "model_dump") else
                p.dict() if hasattr(p, "dict") else dict(p)
                for p in self.dl.read_positions()
            ]
            hedge_manager = _HedgeManager(raw_positions)
            hedges = hedge_manager.get_hedges()
            log.success(
                f"✅ Built {len(hedges)} hedge(s) from {len(raw_positions)} positions",
                source="HedgeCore"
            )
            return hedges
        except Exception as e:
            log.error(f"❌ Hedge update failed: {e}", source="HedgeCore")
            return []

    def build_hedges(self, positions: Optional[List[dict]] = None) -> List[Hedge]:
        """Build :class:`Hedge` objects from position records.

        The returned hedge ID now matches the ``hedge_buddy_id`` used to link
        positions so that consecutive calls yield consistent identifiers.
        """
        if positions is None:
            positions = self.dl.positions.get_all_positions()

        def _get(obj, field, default=None):
            return getattr(obj, field, default) if not isinstance(obj, dict) else obj.get(field, default)

        hedge_groups = {}
        for pos in positions:
            hedge_id = _get(pos, "hedge_buddy_id")
            if hedge_id:
                hedge_groups.setdefault(hedge_id, []).append(pos)

        hedges: List[Hedge] = []
        for key, group in hedge_groups.items():
            if len(group) < 2:
                continue
            # Use the hedge_buddy_id as the Hedge ID so lookups remain stable
            hedge = Hedge(id=str(key))
            hedge.positions = [_get(p, "id") for p in group]

            total_long = total_short = long_heat = short_heat = 0.0
            for p in group:
                ptype = str(_get(p, "position_type", "")).lower()
                size = float(_get(p, "size", 0))
                heat_index = float(_get(p, "heat_index") or 0.0)
                if ptype == "long":
                    total_long += size
                    long_heat += heat_index
                elif ptype == "short":
                    total_short += size
                    short_heat += heat_index

            hedge.total_long_size = total_long
            hedge.total_short_size = total_short
            hedge.long_heat_index = long_heat
            hedge.short_heat_index = short_heat
            hedge.total_heat_index = long_heat + short_heat
            hedge.created_at = datetime.now()
            hedge.updated_at = datetime.now()
            hedge.notes = f"Hedge created from positions with hedge_buddy_id: {key}"

            hedges.append(hedge)

        log.success(
            f"Hedge build complete: {len(hedges)} hedges found.",
            source="HedgeCore",
            payload={"hedge_count": len(hedges)}
        )
        return hedges

    def link_hedges(self) -> List[list]:
        """Scan positions and assign hedge IDs for qualifying groups."""
        positions = self.dl.positions.get_all_positions()

        def _get(obj, field, default=None):
            return getattr(obj, field, default) if not isinstance(obj, dict) else obj.get(field, default)

        groups = {}
        for pos in positions:
            wallet = _get(pos, "wallet_name")
            asset = _get(pos, "asset_type")
            if wallet and asset:
                key = (wallet.strip(), asset.strip())
                groups.setdefault(key, []).append(pos)

        hedged_groups = []
        for key, pos_list in groups.items():
            types = [str(_get(pos, "position_type", "")).strip().lower() for pos in pos_list]
            if "long" in types and "short" in types:
                existing_ids = {_get(p, "hedge_buddy_id") for p in pos_list if _get(p, "hedge_buddy_id")}
                hedge_id = existing_ids.pop() if len(existing_ids) == 1 else str(uuid4())

                for pos in pos_list:
                    if _get(pos, "hedge_buddy_id") != hedge_id:
                        cursor = self.dl.db.get_cursor()
                        cursor.execute(
                            "UPDATE positions SET hedge_buddy_id = ? WHERE id = ?",
                            (hedge_id, _get(pos, "id"))
                        )
                        self.dl.db.commit()
                        cursor.close()
                        if isinstance(pos, dict):
                            pos["hedge_buddy_id"] = hedge_id
                        else:
                            setattr(pos, "hedge_buddy_id", hedge_id)

                hedged_groups.append(pos_list)

        log.success(f"✅ Linked {len(hedged_groups)} hedge group(s)", source="HedgeCore")
        return hedged_groups

    def unlink_hedges(self) -> None:
        """Clear all hedge associations from the database."""
        cursor = self.dl.db.get_cursor()
        cursor.execute(
            "UPDATE positions SET hedge_buddy_id = NULL WHERE hedge_buddy_id IS NOT NULL"
        )
        self.dl.db.commit()
        cursor.close()
        log.success("🧹 Cleared hedge association data", source="HedgeCore")

    def get_modifiers(self, group: str = None) -> dict:
        """Return hedge or heat modifiers via :class:`DLModifierManager`."""
        return self.dl.modifiers.get_all_modifiers(group)

    def get_db_hedges(self) -> List[Hedge]:
        """Retrieve hedges using :class:`DLHedgeManager`."""
        return self.dl.hedges.get_hedges()

