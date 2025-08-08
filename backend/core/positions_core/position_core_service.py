import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from backend.core.positions_core.position_enrichment_service import (
    PositionEnrichmentService,
    validate_enriched_position,
)
from backend.core.positions_core.position_core import PositionCore
from backend.core.calc_core.calculation_core import CalculationCore
from backend.core.logging import log

class PositionCoreService:
    def __init__(self, data_locker):
        self.dl = data_locker

    def fill_positions_with_latest_price(self, positions):
        for pos in positions:
            asset = pos.get('asset_type')
            if asset:
                latest = self.dl.get_latest_price(asset)
                if latest and 'current_price' in latest:
                    try:
                        pos['current_price'] = float(latest['current_price'])
                    except Exception as e:
                        log.warning(f"⚠️ Couldn't parse latest price for {asset}: {e}", source="PositionCoreService")
        return positions

    def update_position_and_alert(self, pos):
        try:
            self.dl.positions.create_position(pos)
            PositionCore.reconcile_wallet_balances(self.dl, {pos.get("wallet_name")})
            log.success(f"✅ Updated position: {pos.get('id')}", source="PositionCoreService")
        except Exception as e:
            log.error(f"❌ update_position_and_alert failed: {e}", source="PositionCoreService")

    def delete_position_and_cleanup(self, position_id: str):
        try:
            cursor = self.dl.db.get_cursor()
            cursor.execute("UPDATE positions SET hedge_buddy_id = NULL WHERE hedge_buddy_id = ?", (position_id,))
            self.dl.db.commit()
            cursor.close()
            log.success(f"💣 Cleared hedge_buddy_id for {position_id}", source="PositionCoreService")

            self.dl.positions.delete_position(position_id)
            log.success(f"✅ Deleted position {position_id}", source="PositionCoreService")

        except Exception as ex:
            log.error(f"❌ Error during delete_position_and_cleanup: {ex}", source="PositionCoreService")

    def record_positions_snapshot(self):
        try:
            positions = PositionCore(self.dl).get_active_positions()
            calc = CalculationCore(self.dl)
            totals = calc.calculate_totals(positions)
            self.dl.portfolio.record_snapshot(totals)

            session = None
            try:
                session = self.dl.session.get_active_session()
                if session:
                    total_val = float(totals.get("total_value", 0.0) or 0.0)
                    delta = total_val - float(session.session_start_value or 0.0)
                    self.dl.session.update_session(
                        session.id,
                        {
                            "current_session_value": delta,
                            "session_performance_value": delta,
                        },
                    )
            except Exception as e:  # pragma: no cover - defensive
                log.error(f"Failed to update session metrics: {e}", source="PositionCoreService")

            log.success(f"📋 Snapshot of {len(positions)} positions recorded.", source="PositionCoreService")
        except Exception as e:
            log.error(f"❌ record_positions_snapshot failed: {e}", source="PositionCoreService")
