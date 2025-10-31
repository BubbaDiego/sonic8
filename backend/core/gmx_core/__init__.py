"""
GMX Core (Phase 1 scaffold)

Purpose
-------
Protocol-specific integration layer for GMX V2 (Arbitrum/Avalanche).
Phase 1 provides file structure + console to verify imports/config paths.
Phase 2+ will implement read path (markets/positions/funding) and writers.

Public Surface (planned)
------------------------
- services.position_source.GMXPositionSource
- services.position_service.PositionService
- dl.positions_writer.write_positions

Do not import clients/adapters directly from external modules; use services only.
"""
__all__ = []
