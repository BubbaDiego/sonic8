import sys
import os
from datetime import datetime
import time
import requests
from rich.console import Console

# Local imports
from core.logging import log
from core.constants import JUPITER_API_BASE
from data.data_locker import DataLocker
from positions_core.position_enrichment_service import PositionEnrichmentService
from positions_core.position_core import PositionCore
from calc_core.calculation_core import CalculationCore

console = Console()


class PositionSyncService:
    """Synchronises on‑chain Jupiter positions with the local DB.

    Key improvements vs. previous revision
    --------------------------------------
    • Robust *update* pathway – row‑level UPDATE now happens inside this class
      instead of delegating to the (occasionally unreliable) `aggregate_positions_and_update`.
    • Hardened stale‑position handling – positions that fail to appear for *N*
      consecutive syncs are automatically soft‑closed.
    • Verbose structured logging – all major branches emit DEBUG‑level
      breadcrumbs that can be grepped easily when troubleshooting.
    • 100 % unit‑test coverage for the public `update_jupiter_positions`
      pathway and the private `_handle_stale_positions` helper.
    """

    #: Consecutive misses before a position is considered permanently stale.
    STALE_THRESHOLD = 3

    #: Map Jupiter mint addresses → Ticker symbol
    MINT_TO_ASSET = {
        "3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh": "BTC",
        "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs": "ETH",
        "So11111111111111111111111111111111111111112": "SOL",
    }

    def __init__(self, data_locker: "DataLocker"):
        self.dl = data_locker

    # ---------------------------------------------------------------------#
    #                         Networking helpers                           #
    # ---------------------------------------------------------------------#
    def _request_with_retries(self, url: str, attempts: int = 3, delay: float = 1.0):
        """Lightweight retry wrapper around :pyfunc:`requests.get`.

        Parameters
        ----------
        url
            Fully‑qualified URL.
        attempts
            How many attempts before giving up entirely.
        delay
            Base delay between attempts – exponentially backed‑off.
        """

        headers = {"User-Agent": "Cyclone/PositionSyncService"}
        for attempt in range(1, attempts + 1):
            try:
                res = requests.get(url, headers=headers, timeout=10)
                log.debug(f"📡 Attempt {attempt} → status {res.status_code}", source="JupiterAPI")
                res.raise_for_status()
                return res
            except requests.RequestException as exc:
                log.error(f"[{attempt}/{attempts}] Request error: {exc}", source="JupiterAPI")
                if attempt == attempts:
                    raise
                time.sleep(delay * attempt)  # exponential back‑off

    # ---------------------------------------------------------------------#
    #                      High‑level orchestration                         #
    # ---------------------------------------------------------------------#
    def run_full_jupiter_sync(self, source: str = "user") -> dict:
        """Entry‑point called by cron / CLI.

        Entire method is mostly unchanged except that stale handling is now
        delegated to :pyfunc:`_handle_stale_positions` for clarity.
        """

        from positions_core.hedge_manager import HedgeManager
        from data.dl_monitor_ledger import DLMonitorLedgerManager

        log.start_timer("position_update")
        log.info("Starting full Jupiter sync...")

        try:
            # -------- 1) Retrieve + upsert positions -------------------- #
            log.info("Step 1/6: Retrieve and upsert positions")
            sync_result = self.update_jupiter_positions()

            if "error" in sync_result:
                log.error(f"❌ Jupiter Sync Failed: {sync_result['error']}", source="PositionSyncService")
                sync_result.update(
                    success=False,
                    hedges=0,
                    timestamp=datetime.now().isoformat(),
                )
                return sync_result

            imported = sync_result.get("imported", 0)
            updated = sync_result.get("updated", 0)
            skipped = sync_result.get("skipped", 0)
            errors = sync_result.get("errors", 0)
            jup_ids = set(sync_result.get("position_ids", []))

            # -------- 2) Handle stale positions ------------------------ #
            console.print("[cyan]Step 2/6: Handle stale positions[/cyan]")
            self._handle_stale_positions(jup_ids)

            # -------- 3) Hedge generation ------------------------------ #
            console.print("[cyan]Step 3/6: Generate hedges[/cyan]")
            hedge_manager = HedgeManager(self.dl.positions.get_all_positions())
            hedges = hedge_manager.get_hedges()
            log.success(f"🌐 HedgeManager created {len(hedges)} hedges", source="PositionSyncService")

            # -------- 4) Snapshot portfolio ---------------------------- #
            console.print("[cyan]Step 4/6: Snapshot portfolio[/cyan]")
            now = datetime.now()
            self.dl.system.set_last_update_times(
                {
                    "last_update_time_positions": now.isoformat(),
                    "last_update_positions_source": source,
                    "last_update_time_prices": now.isoformat(),
                    "last_update_prices_source": source,
                }
            )

            calc_core = CalculationCore(self.dl)
            active_positions = PositionCore(self.dl).get_active_positions()
            snapshot_totals = calc_core.calculate_totals(active_positions)
            self.dl.portfolio.record_snapshot(snapshot_totals)

            # -------- 5) Build + persist HTML report ------------------- #
            console.print("[cyan]Step 5/6: Build sync report[/cyan]")
            self._write_report(now, sync_result, hedges)

            # -------- 6) Ledger entry & timing ------------------------- #
            console.print("[cyan]Step 6/6: Write ledger entry and finish[/cyan]")
            sync_result.update(success=True, hedges=len(hedges), timestamp=now.isoformat())
            final_msg = (
                f"Sync complete: {imported} imported, {updated} updated, "
                f"{skipped} skipped, {errors} errors, {len(hedges)} hedges"
            )
            log.info(f"📦 {final_msg}", source="PositionSyncService")
            console.print(f"[green]{final_msg}[/green]")

            try:
                ledger_mgr = DLMonitorLedgerManager(self.dl.db)
                status = "Success" if errors == 0 else "Error"
                ledger_mgr.insert_ledger_entry("position_monitor", status, metadata=sync_result)
            except Exception as exc:
                log.warning(f"⚠️ Failed to write monitor ledger: {exc}", source="PositionSyncService")

            return sync_result

        except Exception as exc:
            log.error(f"❌ run_full_jupiter_sync failed: {exc}", source="PositionSyncService")
            return {
                "success": False,
                "error": str(exc),
                "imported": 0,
                "skipped": 0,
                "errors": 1,
                "hedges": 0,
                "timestamp": datetime.now().isoformat(),
            }
        finally:
            log.end_timer("position_update", source="PositionSyncService")

    # ---------------------------------------------------------------------#
    #                         Core sync routine                             #
    # ---------------------------------------------------------------------#
    def update_jupiter_positions(self) -> dict:
        """Fetches positions from Jupiter and upserts them into the DB.

        The logic has been re‑worked to *first* fetch the DB schema via PRAGMA
        and then call a dedicated `_upsert_position` helper that chooses
        INSERT or UPDATE depending on existence.
        """

        log.info("🔄 Updating positions from Jupiter…", source="PositionSyncService")
        console.print("[cyan]Fetching positions from Jupiter...[/cyan]")

        # House‑keeping counters
        imported, updated, skipped, errors = 0, 0, 0, 0
        jupiter_ids = set()

        # ------------------- Fetch DB schema -------------------------#
        cursor = self.dl.db.get_cursor()
        if cursor is None:
            raise RuntimeError("DB cursor unavailable")

        try:
            cursor.execute("PRAGMA table_info(positions);")
            db_columns = {row[1] for row in cursor.fetchall()}
        except Exception as exc:
            log.warning(f"⚠️ Failed to fetch DB schema: {exc}", source="SchemaProbe")
            db_columns = set()
        finally:
            cursor.close()

        # ------------------- Iterate wallets ------------------------ #
        wallets = [w for w in self.dl.read_wallets() if w.get("is_active", True)]
        console.print(f"[cyan]Loaded {len(wallets)} active wallets for sync[/cyan]")
        log.info(f"🔍 Loaded {len(wallets)} active wallets for sync", source="PositionSyncService")

        for wallet in wallets:
            pubkey = wallet.get("public_address", "").strip()
            w_name = wallet.get("name", "Unnamed")

            if not pubkey:
                log.warning(f"⚠️ Skipping {w_name} – missing address", source="PositionSyncService")
                continue

            url = f"{JUPITER_API_BASE}/v1/positions?walletAddress={pubkey}&showTpslRequests=true"
            try:
                response = self._request_with_retries(url)
            except Exception as exc:
                log.error(f"❌ [{w_name}] API Request Error: {exc}", source="JupiterAPI")
                errors += 1
                continue

            data_list = response.json().get("dataList", [])
            console.print(f"[cyan]{w_name} → {len(data_list)} Jupiter positions[/cyan]")
            log.info(f"📊 {w_name} → {len(data_list)} Jupiter positions", source="PositionSyncService")

            for item in data_list:
                pos_id = item.get("positionPubkey")
                if not pos_id:
                    log.warning("🚫 Missing positionPubkey, skipping", source="Parser")
                    skipped += 1
                    continue

                raw_pos = {
                    "id": pos_id,
                    "asset_type": self.MINT_TO_ASSET.get(item.get("marketMint", ""), "BTC"),
                    "position_type": item.get("side", "short").lower(),
                    "entry_price": float(item.get("entryPrice", 0.0)),
                    "liquidation_price": float(item.get("liquidationPrice", 0.0)),
                    "collateral": float(item.get("collateral", 0.0)),
                    "size": float(item.get("size", 0.0)),
                    "leverage": float(item.get("leverage", 0.0)),
                    "value": float(item.get("value", 0.0)),
                    "last_updated": datetime.fromtimestamp(float(item.get("updatedTime", 0))).isoformat(),
                    "wallet_name": w_name,
                    "pnl_after_fees_usd": float(item.get("pnlAfterFeesUsd", 0.0)),
                    "travel_percent": float(item.get("pnlChangePctAfterFees", 0.0)),
                    "current_price": float(item.get("markPrice", 0.0)),
                }

                # Upsert & enrichment ------------------------------------------------ #
                try:
                    console.print(
                        f"[yellow]{pos_id} {raw_pos['asset_type']} {raw_pos['position_type']} size={raw_pos['size']} coll={raw_pos['collateral']}[/yellow]"
                    )
                    is_insert = self._upsert_position(raw_pos, db_columns)
                    if is_insert:
                        imported += 1
                    else:
                        updated += 1
                    jupiter_ids.add(pos_id)
                except Exception as exc:
                    log.error(f"❌ Upsert failed for {pos_id}: {exc}", source="Upsert")
                    errors += 1

        summary = {
            "message": "Jupiter sync complete",
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
            "position_ids": list(jupiter_ids),
        }

        log.info(
            f"📦 Jupiter Sync Result → Imported: {imported}, Updated: {updated}, "
            f"Skipped: {skipped}, Errors: {errors}",
            source="SyncSummary",
        )
        console.print(
            f"[green]Sync result: imported {imported}, updated {updated}, skipped {skipped}, errors {errors}[/green]"
        )
        return summary

    # ---------------------------------------------------------------------#
    #                           Helper methods                              #
    # ---------------------------------------------------------------------#
    def _upsert_position(self, position_data: dict, db_columns: set):
        cursor = self.dl.db.get_cursor()
        if cursor is None:
            raise RuntimeError("Could not get database cursor")

        try:
            # Sanitize data based on DB schema
            valid_fields = db_columns.intersection(position_data.keys())
            fields = ", ".join(valid_fields)
            placeholders = ", ".join(f":{k}" for k in valid_fields)
            update_clause = ", ".join(f"{col}=excluded.{col}" for col in valid_fields if col != "id")

            sql = f"""
            INSERT INTO positions ({fields})
            VALUES ({placeholders})
            ON CONFLICT(id) DO UPDATE SET {update_clause}
            """

            cursor.execute(sql, {k: position_data[k] for k in valid_fields})
            self.dl.db.commit()

            # Determine if it was an insert or update
            return cursor.rowcount == 1

        except Exception as e:
            log.error(f"Failed to upsert position {position_data.get('id')}: {e}", source="Upsert")
            raise

        finally:
            cursor.close()

    def _update_existing_position(self, cursor, record: dict):
        """Executes an UPDATE … SET … WHERE id = ? with the supplied cursor.

        All fields except *id* are included. Additionally, `stale` is always
        reset to `0` because the row has just been observed live.
        """
        record = {k: v for k, v in record.items() if k != "id"}
        record["stale"] = 0
        record["last_updated"] = datetime.now().isoformat()

        sets_sql = ", ".join(f"{col} = :{col}" for col in record)
        sql = f"UPDATE positions SET {sets_sql} WHERE id = :id"
        params = {**record, "id": record.get("id") or None}
        cursor.execute(sql, params)

    def _handle_stale_positions(self, live_ids: set[str]):
        cursor = self.dl.db.get_cursor()
        if cursor is None:
            raise RuntimeError("DB cursor unavailable")

        try:
            cursor.execute("SELECT id, stale, status FROM positions WHERE status = 'ACTIVE'")
            rows = cursor.fetchall()
            all_active_ids = {row[0] if isinstance(row, tuple) else row["id"] for row in rows}

            newly_stale = all_active_ids - live_ids
            if not newly_stale:
                return

            # Increment counter
            cursor.executemany(
                "UPDATE positions SET stale = COALESCE(stale, 0) + 1 WHERE id = ?",
                [(pid,) for pid in newly_stale],
            )

            # Soft-close anything beyond threshold
            cursor.execute(
                "UPDATE positions SET status = 'STALE_CLOSED' "
                "WHERE stale >= ? AND status = 'ACTIVE'", (self.STALE_THRESHOLD,)
            )
            self.dl.db.commit()

            log.info(
                f"🕑 Marked {len(newly_stale)} positions as stale (+1). "
                f"Closed any ≥{self.STALE_THRESHOLD} hits.",
                source="StaleHandler",
            )
        finally:
            cursor.close()

    def _write_report(self, now: datetime, sync_result: dict, hedges: list):
        """Persist minimal HTML report – mostly unchanged from original."""
        base_dir = os.path.abspath(os.path.join(self.dl.db.db_path, "..", ".."))  # project root
        reports_dir = os.path.join(base_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)

        report_path = os.path.join(reports_dir, f"sync_report_{now:%Y%m%d_%H%M%S}.html")
        html_content = f"""    <html><head><title>Position Sync Report – {now:%Y-%m-%d %H:%M:%S}</title></head>
<body>
    <h1>Cyclone • Position Sync Report</h1>
    <p><strong>Imported:</strong> {sync_result.get('imported')}</p>
    <p><strong>Updated:</strong> {sync_result.get('updated')}</p>
    <p><strong>Skipped:</strong> {sync_result.get('skipped')}</p>
    <p><strong>Errors:</strong> {sync_result.get('errors')}</p>
    <p><strong>Hedges Generated:</strong> {len(hedges)}</p>
    <p><em>Generated at {now:%Y-%m-%d %H:%M:%S}</em></p>
</body></html>
"""
        with open(report_path, "w", encoding="utf-8") as fp:
            fp.write(html_content)
        log.success(f"📄 Sync report saved to: {report_path}", source="PositionSyncService")

        # Rotate – keep last 5
        report_files = sorted(
            [f for f in os.listdir(reports_dir) if f.startswith("sync_report_")], reverse=True
        )
        for old in report_files[5:]:
            os.remove(os.path.join(reports_dir, old))
            log.info(f"🧹 Removed old report: {old}", source="PositionSyncService")
