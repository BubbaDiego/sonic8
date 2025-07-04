"""Top-level re-exports for position helpers."""

__all__ = [
    "PositionCore",
    "PositionSyncService",
    "PositionCoreService",
    "HedgeManager",
]


def __getattr__(name):
    if name == "PositionCore":
        from backend.core.positions_core.position_core import PositionCore
        return PositionCore
    if name == "PositionSyncService":
        from backend.core.positions_core.position_sync_service import PositionSyncService
        return PositionSyncService
    if name == "PositionCoreService":
        from backend.core.positions_core.position_core_service import PositionCoreService
        return PositionCoreService
    if name == "HedgeManager":
        from backend.core.positions_core.hedge_manager import HedgeManager
        return HedgeManager
    raise AttributeError(name)
