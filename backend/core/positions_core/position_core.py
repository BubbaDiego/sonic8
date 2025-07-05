# positions/position_core.py
import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from backend.core.core_imports import log
from backend.core.positions_core.position_store import PositionStore
from backend.core.positions_core.position_enrichment_service import PositionEnrichmentService
from backend.core.positions_core.position_enrichment_service import validate_enriched_position
from backend.core.hedge_core.hedge_core import HedgeCore
from backend.core.calc_core.calc_services import CalcServices
from datetime import datetime
import uuid
from backend.models.position import PositionDB

class PositionCore:
    def __init__(self, data_locker):
        self.dl = data_locker
        self.store = PositionStore(data_locker)
        self.enricher = PositionEnrichmentService(data_locker)

    @staticmethod
    def reconcile_wallet_balances(dl, wallets: set[str] | None = None) -> int:
        """Recalculate balances for the specified wallets.

        Parameters
        ----------
        dl
            DataLocker instance used to access wallets and positions.
        wallets
            Optional set of wallet names to refresh. If ``None`` all active
            wallets are recalculated.

        Returns
        -------
        int
            Number of wallets successfully updated.
        """

        from backend.core.wallet_core import WalletCore

        wc = WalletCore()
        if wallets:
            updated = 0
            for w in wallets:
                if wc.refresh_wallet_balance(w):
                    updated += 1
            return updated
        return wc.refresh_wallet_balances()

    def get_all_positions(self):
        return self.store.get_all_positions()

    def get_active_positions(self):
        """Return active positions for wallets marked as active."""
        positions = self.store.get_active_positions()
        try:
            wallets = self.dl.read_wallets()
            if not wallets:
                return positions
            inactive = {w.get("name") for w in wallets if not w.get("is_active", True)}
            if not inactive:
                return positions
            filtered = [
                p
                for p in positions
                if getattr(p, "wallet_name", getattr(p, "wallet", None)) not in inactive
            ]
            return filtered
        except Exception:
            return positions

    def create_position(self, pos):
        """Enrich and insert a position. ``pos`` may be ``dict`` or ``PositionDB``."""
        if isinstance(pos, PositionDB):
            pos_data = pos.model_dump() if hasattr(pos, "model_dump") else pos.dict()
        else:
            pos_data = pos
        enriched = self.enricher.enrich(pos_data)
        obj = PositionDB(**enriched)
        inserted = self.store.insert(obj)
        if inserted:
            try:
                HedgeCore(self.dl).update_hedges()
            except Exception as e:  # pragma: no cover - just log
                log.error(f"Failed to update hedges after insert: {e}", source="PositionCore")
            try:
                self.reconcile_wallet_balances(self.dl, {obj.wallet_name})
            except Exception as e:  # pragma: no cover - just log
                log.error(f"Failed to refresh wallet balance: {e}", source="PositionCore")
        return inserted

    def delete_position(self, pos_id: str):
        wallet = None
        try:
            record = self.store.get_by_id(pos_id)
            wallet = getattr(record, "wallet_name", None) if record else None
        except Exception:
            wallet = None

        deleted = self.store.delete(pos_id)
        if deleted and wallet:
            try:
                self.reconcile_wallet_balances(self.dl, {wallet})
            except Exception as e:  # pragma: no cover - just log
                log.error(f"Failed to refresh wallet balance: {e}", source="PositionCore")
        return deleted

    def clear_all_positions(self):
        self.store.delete_all()

    def record_snapshot(self):
        """Persist a snapshot of active positions, excluding inactive wallets."""
        try:
            raw = self.get_active_positions()
            totals = CalcServices().calculate_totals(raw)
            self.dl.portfolio.record_snapshot(totals)
            log.success("📸 Position snapshot recorded", source="PositionCore")
        except Exception as e:
            log.error(f"❌ Snapshot recording failed: {e}", source="PositionCore")

    def update_positions_from_jupiter(self, source="console"):
        """
        Legacy passthrough for console + engine.
        Uses PositionSyncService under the hood.
        """
        from backend.core.positions_core.position_sync_service import (
            PositionSyncService,
        )
        sync_service = PositionSyncService(self.dl)
        return sync_service.run_full_jupiter_sync(source=source)

    def link_hedges(self):
        """
        Runs hedge detection and returns a list of generated Hedge objects.
        """
        log.banner("🔗 Generating Hedges via PositionCore")

        try:
            core = HedgeCore(self.dl)
            groups = core.link_hedges()
            log.info(
                f"📥 Linked {len(groups)} hedge group(s)",
                source="PositionCore",
            )

            hedges = core.build_hedges()
            log.success(
                "✅ Hedge generation complete",
                source="PositionCore",
                payload={"hedge_count": len(hedges)},
            )
            return hedges

        except Exception as e:
            log.error(f"❌ Failed to generate hedges: {e}", source="PositionCore")
            return []

    async def enrich_positions(self):
        """
        Enriches all current positions and returns the list.
        Performs validation after enrichment.
        """
        log.banner("🧠 Enriching All Positions via PositionCore")

        try:
            raw = self.store.get_all()
            enriched = []
            failed = []

            for pos in raw:
                try:
                    enriched_pos = self.enricher.enrich(pos)

                    if validate_enriched_position(enriched_pos, source="EnrichmentValidator"):
                        enriched.append(enriched_pos)
                    else:
                        failed.append(enriched_pos.get("id"))

                except Exception as e:
                    log.error(f"⚠️ Failed to enrich position {pos.get('id')}: {e}", source="PositionCore")

            log.success("✅ Position enrichment complete", source="PositionCore", payload={
                "enriched": len(enriched),
                "failed": len(failed)
            })

            if failed:
                log.warning("⚠️ Some positions failed enrichment validation", source="PositionCore", payload={
                    "invalid_ids": failed
                })

            return enriched

        except Exception as e:
            log.error(f"❌ enrich_positions() failed: {e}", source="PositionCore")
            return []


class TransactionService:
    def __init__(self, data_locker):
        self.dl = data_locker

    def reconstruct_transactions(self):
        cursor = self.dl.db.get_cursor()
        if not cursor:
            log.error("❌ DB unavailable", source="TransactionService")
            return []

        try:
            cursor.execute(
                "SELECT * FROM position_events ORDER BY position_id, ts ASC"
            )
            rows = [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            log.error(
                f"❌ Failed to fetch position events: {e}",
                source="TransactionService",
            )
            return []

        events_by_pos = {}
        for row in rows:
            events_by_pos.setdefault(row.get("position_id"), []).append(row)

        transactions = []
        for pos_id, events in events_by_pos.items():
            for prev, curr in zip(events, events[1:]):
                delta_val = curr.get("value", 0) - prev.get("value", 0)
                if abs(delta_val) <= 0.0001:
                    continue

                curr_size = curr.get("size")
                prev_size = prev.get("size")
                delta_size = (
                    curr_size - prev_size
                    if curr_size is not None and prev_size is not None
                    else delta_val
                )
                price = (
                    curr.get("price")
                    or (curr.get("value", 0) / curr_size if curr_size else 0)
                )

                tx = {
                    "event_id": str(uuid.uuid4()),
                    "order_id": None,
                    "position_id": pos_id,
                    "trader_name": curr.get("trader_name"),
                    "ts": curr.get("ts"),
                    "asset_type": curr.get("asset_type"),
                    "side": "BUY" if delta_val > 0 else "SELL",
                    "size": delta_size,
                    "price": price,
                    "fees": 0,
                    "pnl_estimated": curr.get("pnl_after_fees"),
                    "classification": "INFERRED",
                    "pre_value": prev.get("value"),
                    "post_value": curr.get("value"),
                    "delta_value": delta_val,
                    "notes": "{\"inferred\": true}",
                }
                transactions.append(tx)

        for tx in transactions:
            cols = ", ".join(tx.keys())
            placeholders = ", ".join(f":{k}" for k in tx.keys())
            cursor.execute(
                f"INSERT INTO transaction_events ({cols}) VALUES ({placeholders})",
                tx,
            )
        self.dl.db.commit()
        log.success(
            f"Reconstructed {len(transactions)} transactions.",
            source="TransactionService",
        )
        return transactions

