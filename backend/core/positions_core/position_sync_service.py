import os
import time
from datetime import datetime

import requests
from rich.console import Console

from backend.core.reporting_core.task_events import phase_end, phase_start
from backend.core.reporting_core.positions_icons import compute_from_list
from backend.core.reporting_core.summary_cache import set_positions_icon_line, set_hedges

# Core / services
from backend.core.logging import log
from backend.core.core_constants import JUPITER_API_BASE
from backend.data.data_locker import DataLocker
from backend.core.positions_core.position_enrichment_service import PositionEnrichmentService
from backend.data.dl_positions import DLPositionManager
from backend.core.positions_core.position_core import PositionCore
from backend.core.calc_core.calculation_core import CalculationCore
from backend.core.hedge_core.hedge_core import HedgeCore
from backend.core.trader_core import TraderUpdateService
from backend.services.signer_loader import load_signer
from backend.utils.pubkey import extract_pubkey, is_base58_pubkey

console = Console()
_VERBOSE = os.getenv("SONIC_TASKS_VERBOSE", "0").strip().lower() in {"1", "true", "yes"}

def _extract_wallet_pubkey(wallet: dict) -> tuple[str, str]:
    """Return the first valid base58 pubkey found in *wallet* (if any)."""

    if not isinstance(wallet, dict):
        return "", ""

    candidates: list[str] = []
    for key in ("public_address", "address", "pubkey", "wallet_address"):
        raw = wallet.get(key)
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            candidates.append(text)

    for raw in candidates:
        candidate = extract_pubkey(raw)
        if is_base58_pubkey(candidate):
            return candidate, raw

    return "", candidates[0] if candidates else ""

# Optional override; if unset we select perps-api explicitly
JUPITER_PERPS_API_BASE = os.getenv("JUPITER_PERPS_API_BASE", "").strip()


class PositionSyncService:
    """Synchronises Jupiter **Perps** positions with the local DB."""

    # how many consecutive misses before marking stale
    STALE_THRESHOLD = 3

    # Jupiter mints → asset symbols (extend if you trade more)
    MINT_TO_ASSET = {
        "3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh": "BTC",
        "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs": "ETH",
        "So11111111111111111111111111111111111111112": "SOL",
    }

    def __init__(self, data_locker: "DataLocker"):
        self.dl = data_locker
        # Ensure the 'positions' table exists and is up to date (fresh DB safety)
        try:
            DLPositionManager.ensure_schema(self.dl.db)
        except Exception as e:
            log.warning(f"Schema ensure skipped: {e}", source="PositionSyncService")
        self.enricher = PositionEnrichmentService(data_locker)

    # ------------------------------ HTTP helpers ------------------------------ #

    def _pick_api_base(self) -> str:
        """
        Prefer env override; otherwise prefer the Perps base explicitly.
        If your JUPITER_API_BASE already points to perps it still works.
        """
        base = (JUPITER_PERPS_API_BASE or JUPITER_API_BASE).rstrip("/")
        if "perps-api" not in base:
            base = "https://perps-api.jup.ag"
        log.info(f"[PerpsSync] Using Jupiter base: {base}", source="PositionSyncService")
        return base

    def _request_with_retries(self, url: str, attempts: int = 3, delay: float = 1.0):
        headers = {"User-Agent": "Cyclone/PositionSyncService"}
        last_exc: Exception | None = None
        for i in range(1, attempts + 1):
            try:
                r = requests.get(url, headers=headers, timeout=(2.0, 4.0))
                log.debug(f"📡 GET {url} (attempt {i}) → {r.status_code}", source="JupiterAPI")
                r.raise_for_status()
                return r
            except requests.Timeout as exc:
                last_exc = exc
                log.error(f"[{i}/{attempts}] Request timeout: {exc}", source="JupiterAPI")
            except requests.RequestException as exc:
                last_exc = exc
                log.error(f"[{i}/{attempts}] Request error: {exc}", source="JupiterAPI")
            if i < attempts:
                time.sleep(delay * i)
        if last_exc:
            raise last_exc
        raise RuntimeError("Jupiter perps request failed without exception")

    @staticmethod
    def _extract_positions(payload: dict) -> list:
        """
        Accept common Jupiter response shapes:
          - dataList: [...]
          - data: {...} (try items/data/list)
          - positions / items / result: [...]
          - single object with positionPubkey / id / position
        """
        if not isinstance(payload, dict):
            return []
        for k in ("dataList", "data", "positions", "items", "result"):
            v = payload.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                for kk in ("items", "data", "list"):
                    vv = v.get(kk)
                    if isinstance(vv, list):
                        return vv
        if any(k in payload for k in ("positionPubkey", "id", "position")):
            return [payload]
        return []

    # ------------------------------ Orchestration ----------------------------- #

    def run_full_jupiter_sync(self, source: str = "user") -> dict:
        """
        Main entrypoint used by your scheduler / UI. Fetch → upsert → snapshot → report.
        """
        from backend.core.positions_core.hedge_manager import HedgeManager
        from data.dl_monitor_ledger import DLMonitorLedgerManager

        log.start_timer("position_update")
        log.info("Starting full Jupiter Perps sync...")

        try:
            phase_start("positions_fetch", "Fetching positions from Jupiter perps-api")
            try:
                sync = self.update_jupiter_positions()
            except Exception as exc:
                phase_end("positions_fetch", "fail", note=str(exc))
                raise

            errors = sync.get("errors", 0)
            fetch_note: str | None = None
            verdict = "ok"

            # Use richer error info from update_jupiter_positions()
            if "error" in sync:
                verdict = "fail"
                fetch_note = sync.get("error")
            elif errors:
                verdict = "warn"
                preview = sync.get("error_preview")
                if preview:
                    fetch_note = f"{errors} errors – {preview}"
                else:
                    fetch_note = f"{errors} errors"

            phase_end("positions_fetch", verdict, note=fetch_note)

            if "error" in sync:
                log.error(f"❌ Perps Sync Failed: {sync['error']}", source="PositionSyncService")
                sync.update(success=False, hedges=0, timestamp=datetime.now().isoformat())
                return sync

            imported = sync.get("imported", 0)
            updated = sync.get("updated", 0)
            skipped = sync.get("skipped", 0)
            errors = sync.get("errors", 0)
            live_ids = set(sync.get("position_ids", []))

            # stale handling
            if _VERBOSE:
                console.print("[cyan]Handle stale positions[/cyan]")
            phase_start("positions_stale", "Handle stale positions")
            try:
                self._handle_stale_positions(live_ids)
            except Exception as exc:
                phase_end("positions_stale", "fail", note=str(exc))
                raise
            else:
                phase_end("positions_stale", "ok")

            # hedges
            if _VERBOSE:
                console.print("[cyan]Generate hedges[/cyan]")
            phase_start("hedges", "Generate hedges")
            try:
                hedges = HedgeManager(self.dl.positions.get_all_positions()).get_hedges()
            except Exception as exc:
                phase_end("hedges", "fail", note=str(exc))
                raise
            else:
                phase_end("hedges", "ok")
            log.success(f"🌐 HedgeManager produced {len(hedges)} hedges", source="PositionSyncService")
            try:
                set_hedges(len(hedges))
            except Exception:
                pass
            try:
                setattr(self.dl, "last_hedge_groups", int(len(hedges)))
            except Exception:
                pass

            # snapshot
            if _VERBOSE:
                console.print("[cyan]Snapshot portfolio[/cyan]")
            now = datetime.now()
            phase_start("snapshot", "Snapshot portfolio")
            try:
                self.dl.system.set_last_update_times(
                    {
                        "last_update_time_positions": now.isoformat(),
                        "last_update_positions_source": source,
                        "last_update_time_prices": now.isoformat(),
                        "last_update_prices_source": source,
                    }
                )
                totals = CalculationCore(self.dl).calculate_totals(PositionCore(self.dl).get_active_positions())
                self.dl.portfolio.record_snapshot(totals)
            except Exception as exc:
                phase_end("snapshot", "fail", note=str(exc))
                raise
            else:
                phase_end("snapshot", "ok")

            # simple HTML report (keeps your prior behavior)
            if _VERBOSE:
                console.print("[cyan]Write sync report[/cyan]")
            phase_start("report", "Write sync report")
            try:
                self._write_report(now, sync, hedges)
            except Exception as exc:
                phase_end("report", "fail", note=str(exc))
                raise
            else:
                phase_end("report", "ok")

            # reconcile wallets shown in UI
            PositionCore.reconcile_wallet_balances(self.dl)

            msg = f"   Sync complete: {imported} imported, {updated} updated, {skipped} skipped, {errors} errors"
            log.info(f"📦 {msg}", source="PositionSyncService")
            console.print(f"[green]{msg}[/green]")

            phase_start("sync_summary", "Sync summary")
            try:
                verdict = "ok" if errors == 0 else "warn"
                if errors:
                    preview = sync.get("error_preview")
                    note = f"{errors} errors" if not preview else f"{errors} errors – {preview}"
                else:
                    note = None
                phase_end("sync_summary", verdict, note=note)
            except Exception:
                phase_end("sync_summary", "warn")

            try:
                DLMonitorLedgerManager(self.dl.db).insert_ledger_entry(
                    "position_monitor",
                    "Success" if errors == 0 else "Error",
                    metadata=sync,
                )
            except Exception as e:
                log.warning(f"Ledger entry failed: {e}", source="PositionSyncService")

            sync.update(success=True, hedges=len(hedges), timestamp=now.isoformat())
            return sync

        except Exception as exc:
            log.error(f"❌ run_full_jupiter_sync failed: {exc}", source="PositionSyncService")
            return {"success": False, "error": str(exc), "imported": 0, "skipped": 0, "errors": 1, "hedges": 0}
        finally:
            log.end_timer("position_update", source="PositionSyncService")

    # ------------------------------ Fetch & Upsert ---------------------------- #

    def update_jupiter_positions(self) -> dict:
        """Fetch perps positions from Jupiter and upsert into DB."""
        log.info("🔄 Updating Jupiter Perps positions…", source="PositionSyncService")
        if _VERBOSE:
            console.print("[cyan]Fetching positions from Jupiter perps-api...[/cyan]")

        imported = updated = skipped = errors = 0
        jup_ids: set[str] = set()
        fetched_positions: list[dict] = []
        fallback_positions: list[dict] | None = None
        timeout_triggered = False
        # New: accumulate short, human-friendly error explanations
        error_details: list[str] = []

        # probe DB schema to pass only valid columns on upsert
        cur = self.dl.db.get_cursor()
        if cur is None:
            raise RuntimeError("DB cursor unavailable")
        try:
            cur.execute("PRAGMA table_info(positions);")
            db_cols = {row[1] for row in cur.fetchall()}
            if not db_cols:
                # Fresh DB or table missing → create/repair schema and retry
                try:
                    DLPositionManager.ensure_schema(self.dl.db)
                    cur.execute("PRAGMA table_info(positions);")
                    db_cols = {row[1] for row in cur.fetchall()}
                except Exception as e2:
                    log.error(f"Positions schema creation failed: {e2}", source="SchemaProbe")
                    db_cols = set()
        except Exception as e:
            log.warning(f"Failed to read positions schema: {e}", source="SchemaProbe")
            db_cols = set()
        finally:
            cur.close()

        # wallets to check: DB actives + always include server signer the UI is using
        wallets = [w for w in self.dl.read_wallets() if w.get("is_active", True)]
        try:
            signer_pk = str(load_signer().pubkey()).strip()
        except Exception:
            signer_pk = None
        if signer_pk and all((w.get("public_address") or "").strip() != signer_pk for w in wallets):
            wallets.append({"public_address": signer_pk, "name": "Signer", "is_active": True})

        base = self._pick_api_base()

        for w in wallets:
            name = w.get("name", "Unnamed")
            addr, raw_addr = _extract_wallet_pubkey(w)

            if not raw_addr:
                log.warning(f"Skipping wallet with no address (name={name})", source="PositionSyncService")
                continue

            if not addr:
                log.warning(
                    f"Skipping wallet '{name}': unable to derive base58 pubkey from '{raw_addr}'",
                    source="PositionSyncService",
                )
                continue

            url = f"{base}/v1/positions?walletAddress={addr}&showTpslRequests=true"
            log.debug(f"[PerpsSync] GET {url}", source="JupiterAPI")

            try:
                res = self._request_with_retries(url)
            except requests.Timeout as e:
                errors += 1
                timeout_triggered = True
                msg = f"timeout for wallet '{name}': {e}"
                error_details.append(msg)
                log.error(f"API timeout for {name}: {e}", source="JupiterAPI")
                fallback_positions = self._positions_fallback()
                break
            except requests.RequestException as e:
                errors += 1
                msg = f"request error for wallet '{name}': {e}"
                error_details.append(msg)
                log.error(f"API error for {name}: {e}", source="JupiterAPI")
                continue
            except Exception as e:
                errors += 1
                msg = f"unexpected API error for wallet '{name}': {e}"
                error_details.append(msg)
                log.error(f"API error for {name}: {e}", source="JupiterAPI")
                continue

            if timeout_triggered:
                break

            try:
                payload = res.json() or {}
            except Exception as e:
                errors += 1
                msg = f"JSON parse error for wallet '{name}': {e}"
                error_details.append(msg)
                log.error(f"JSON parse error for {name}: {e}", source="JupiterAPI")
                continue

            items = self._extract_positions(payload)
            console.print(f"[cyan]{name} → {len(items)} Jupiter positions[/cyan]")
            log.info(f"📊 {name} → {len(items)} Jupiter positions", source="PositionSyncService")

            for it in items:
                # id
                pos_id = it.get("positionPubkey") or it.get("position") or it.get("id")
                if not pos_id:
                    skipped += 1
                    log.warning("Missing positionPubkey/id; skipping item", source="Parser")
                    continue

                # market → asset
                market_mint = it.get("marketMint")
                if not market_mint and isinstance(it.get("market"), dict):
                    market_mint = it["market"].get("mint")

                # numeric fields come back as strings; coerce safely
                def f(x, default=0.0):
                    try:
                        return float(x)
                    except Exception:
                        return default

                ts = f(it.get("updatedTime", 0.0))
                if ts > 1e12:  # ms → s
                    ts /= 1000.0

                raw = {
                    "id": pos_id,
                    "asset_type": self.MINT_TO_ASSET.get(market_mint or "", "BTC"),
                    "position_type": str(it.get("side", "short")).lower(),
                    "entry_price": f(it.get("entryPrice")),
                    "liquidation_price": f(it.get("liquidationPrice")),
                    "collateral": f(it.get("collateral")),
                    "size": f(it.get("size")),
                    "leverage": f(it.get("leverage")),
                    "value": f(it.get("value")),
                    "last_updated": datetime.fromtimestamp(ts or 0.0).isoformat(),
                    "wallet_name": name,
                    "pnl_after_fees_usd": f(it.get("pnlAfterFeesUsd")),
                    "travel_percent": f(it.get("pnlChangePctAfterFees")),
                    "current_price": f(it.get("markPrice")),
                }

                fetched_positions.append(
                    {
                        "asset": raw.get("asset_type"),
                        "side": raw.get("position_type"),
                        "is_open": True,
                    }
                )

                try:
                    enriched = self.enricher.enrich(raw)
                    is_insert = self._upsert_position(enriched, db_cols)
                    imported += 1 if is_insert else 0
                    updated += 0 if is_insert else 1
                    jup_ids.add(pos_id)
                except Exception as e:
                    errors += 1
                    msg = f"upsert failed for {pos_id}: {e}"
                    error_details.append(msg)
                    log.error(f"Upsert failed for {pos_id}: {e}", source="Upsert")

        if timeout_triggered:
            fallback_positions = fallback_positions or self._positions_fallback()
            summary = {
                "message": "Jupiter Perps sync fallback (cached snapshot)",
                "imported": 0,
                "updated": 0,
                "skipped": skipped,
                "errors": errors,
                "position_ids": list(jup_ids),
                "fallback": True,
                "success": False,
            }
            if error_details:
                summary["error_details"] = error_details
                summary["error_preview"] = "; ".join(error_details[:3])
            if fallback_positions:
                fetched_positions = fallback_positions
            self._stash_last_positions(fetched_positions)
            return summary

        summary = {
            "message": "Jupiter Perps sync complete",
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
            "position_ids": list(jup_ids),
            "success": True,
        }
        if error_details:
            summary["error_details"] = error_details
            summary["error_preview"] = "; ".join(error_details[:3])

        log.info(
            f"📦 Perps Sync Result → Imported:{imported} Updated:{updated} Skipped:{skipped} Errors:{errors}",
            source="SyncSummary",
        )
        self._stash_last_positions(fetched_positions)
        return summary

    # ------------------------------ DB helpers ------------------------------- #

    def _stash_last_positions(self, positions: list[dict]) -> None:
        line: str | None = None
        try:
            setattr(self.dl, "last_positions_fetch", list(positions))
        except Exception:
            pass
        try:
            line = compute_from_list(positions)
        except Exception:
            line = None
        if line:
            try:
                set_positions_icon_line(
                    line=line,
                    updated_iso=datetime.utcnow().isoformat(),
                    reason="fetched",
                )
            except Exception:
                pass
        try:
            setattr(self.dl, "last_positions_icon_line", line)
        except Exception:
            pass

    def _positions_fallback(self) -> list[dict]:
        cache = getattr(self.dl, "last_positions_fetch", None)
        if isinstance(cache, list) and cache:
            return [dict(item) if isinstance(item, dict) else dict(getattr(item, "__dict__", {})) for item in cache]

        try:
            pos_mgr = getattr(self.dl, "positions", None)
            if pos_mgr and hasattr(pos_mgr, "get_all_positions"):
                rows = pos_mgr.get_all_positions() or []
                normalized: list[dict] = []
                for row in rows:
                    if isinstance(row, dict):
                        normalized.append(dict(row))
                    else:
                        normalized.append(dict(getattr(row, "__dict__", {})))
                if normalized:
                    return normalized
        except Exception:
            pass

        try:
            system_mgr = getattr(self.dl, "system", None)
            if system_mgr:
                snapshot = system_mgr.get_var("positions_snapshot")
                if isinstance(snapshot, list) and snapshot:
                    return [dict(item) if isinstance(item, dict) else dict(getattr(item, "__dict__", {})) for item in snapshot]
        except Exception:
            pass

        return []

    def _upsert_position(self, position_data: dict, db_columns: set) -> bool:
        """
        INSERT or UPDATE into positions table using ON CONFLICT(id) DO UPDATE.
        Ensures rows are marked ACTIVE by default and not stale.
        Returns True if inserted, False if updated.
        """
        cur = self.dl.db.get_cursor()
        if cur is None:
            raise RuntimeError("Could not get database cursor")

        try:
            # apply sane defaults if those columns exist
            record = dict(position_data)
            if "status" in db_columns and "status" not in record:
                record["status"] = "ACTIVE"
            if "stale" in db_columns and "stale" not in record:
                record["stale"] = 0
            if "source" in db_columns and "source" not in record:
                record["source"] = "jupiter-perps"

            valid = db_columns.intersection(record.keys())
            if not valid:
                log.warning("No overlapping columns with positions table; skipping upsert",
                            source="PositionSyncService")
                return False

            existing = False
            if "id" in record:
                cur.execute("SELECT 1 FROM positions WHERE id = ?", (record["id"],))
                existing = cur.fetchone() is not None

            cols = ", ".join(valid)
            vals = ", ".join(f":{k}" for k in valid)
            updates = ", ".join(f"{c}=excluded.{c}" for c in valid if c != "id")

            sql = f"INSERT INTO positions ({cols}) VALUES ({vals}) ON CONFLICT(id) DO UPDATE SET {updates}"
            cur.execute(sql, {k: record[k] for k in valid})
            self.dl.db.commit()

            # best-effort refreshes
            try:
                HedgeCore(self.dl).update_hedges()
            except Exception as e:
                log.error(f"Hedge update error: {e}", source="PositionSyncService")
            try:
                TraderUpdateService(self.dl).refresh_trader_for_wallet(record.get("wallet_name", ""))
            except Exception as e:
                log.error(f"Trader refresh error: {e}", source="PositionSyncService")

            return not existing
        finally:
            cur.close()

    def _handle_stale_positions(self, live_ids: set[str]):
        cur = self.dl.db.get_cursor()
        if cur is None:
            raise RuntimeError("DB cursor unavailable")
        try:
            cur.execute("SELECT id, wallet_name, stale, status FROM positions WHERE status = 'ACTIVE'")
            rows = cur.fetchall()
            active_ids = {row[0] if isinstance(row, tuple) else row["id"] for row in rows}
            newly_stale = active_ids - live_ids
            if not newly_stale:
                return

            cur.executemany("UPDATE positions SET stale = COALESCE(stale,0)+1 WHERE id = ?", [(pid,) for pid in newly_stale])
            cur.execute(
                "UPDATE positions SET status = 'STALE_CLOSED' WHERE stale >= ? AND status = 'ACTIVE'",
                (self.STALE_THRESHOLD,),
            )
            self.dl.db.commit()

            # reconcile affected wallets so UI balances don't lag
            affected_names = {
                (row[1] if isinstance(row, tuple) else row["wallet_name"])
                for row in rows if (row[0] if isinstance(row, tuple) else row["id"]) in newly_stale
            }
            PositionCore.reconcile_wallet_balances(self.dl, affected_names)
        finally:
            cur.close()

    def _write_report(self, now: datetime, sync_result: dict, hedges: list):
        """Small HTML report kept from earlier versions."""
        base_dir = os.path.abspath(os.path.join(self.dl.db.db_path, "..", ".."))
        reports_dir = os.path.join(base_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)

        path = os.path.join(reports_dir, f"sync_report_{now:%Y%m%d_%H%M%S}.html")
        html = f"""<html><head><title>Position Sync Report – {now:%Y-%m-%d %H:%M:%S}</title></head>
<body>
  <h1>Cyclone • Position Sync Report</h1>
  <p><strong>Imported:</strong> {sync_result.get('imported')}</p>
  <p><strong>Updated:</strong> {sync_result.get('updated')}</p>
  <p><strong>Skipped:</strong> {sync_result.get('skipped')}</p>
  <p><strong>Errors:</strong> {sync_result.get('errors')}</p>
  <p><strong>Hedges Generated:</strong> {len(hedges)}</p>
  <p><em>Generated at {now:%Y-%m-%d %H:%M:%S}</em></p>
</body></html>"""
        with open(path, "w", encoding="utf-8") as fp:
            fp.write(html)
        log.success(f"📄 Sync report saved to: {path}", source="PositionSyncService")

        # rotate – keep last 5
        files = sorted([f for f in os.listdir(reports_dir) if f.startswith("sync_report_")], reverse=True)
        for old in files[5:]:
            os.remove(os.path.join(reports_dir, old))
            log.info(f"🧹 Removed old report: {old}", source="PositionSyncService")
