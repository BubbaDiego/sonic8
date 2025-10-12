import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional, Callable


def _resolve_and_load_env() -> str | None:
    """
    Find the intended .env file and load it once.
    Priority:
      1) SONIC_ENV_PATH (explicit override)
      2) repo root /.env
      3) backend/.env
      4) CWD/.env
      5) python-dotenv discovery (find_dotenv)
    Saves the resolved path into SONIC_ENV_PATH_RESOLVED for banner usage.
    """

    try:
        from dotenv import load_dotenv, find_dotenv  # type: ignore
    except Exception:
        return None

    here = Path(__file__).resolve()
    repo_root = here.parents[3] if len(here.parents) >= 4 else Path.cwd()

    candidates: list[Path] = []
    explicit = os.getenv("SONIC_ENV_PATH")
    if explicit:
        candidates.append(Path(explicit))
    candidates.extend([
        repo_root / ".env",
        repo_root / "backend" / ".env",
        Path.cwd() / ".env",
    ])

    chosen: Path | None = None
    for path_candidate in candidates:
        try:
            if path_candidate and path_candidate.exists():
                chosen = path_candidate
                break
        except Exception:
            pass

    if chosen is None:
        try:
            found = find_dotenv(usecwd=True)
            if found:
                chosen = Path(found)
        except Exception:
            chosen = None

    if chosen is not None:
        try:
            load_dotenv(dotenv_path=str(chosen), override=False)
            os.environ["SONIC_ENV_PATH_RESOLVED"] = str(chosen)
        except Exception:
            pass
        return str(chosen)

    return None


_env_used = _resolve_and_load_env()

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
import asyncio
import logging
import time
from datetime import datetime, timezone

from backend.core.monitor_core.utils.console_title import set_console_title
from backend.core.cyclone_core.cyclone_engine import Cyclone
from backend.core.monitor_core.utils.banner import emit_config_banner
from backend.core.monitor_core.sonic_events import notify_listeners
from backend.core.reporting_core.task_events import task_start, task_end
from backend.core.reporting_core.console_lines import emit_compact_cycle
from backend.core.reporting_core.positions_icons import compute_positions_icon_line
from backend.core.reporting_core.console_reporter import (
    emit_boot_status,
    emit_dashboard_link,
    install_strict_console_filter,
    neuter_legacy_console_logger,
    silence_legacy_console_loggers,
)
from backend.core.reporting_core.prelaunch import print_prelaunch_checklist
from data.data_locker import DataLocker
from backend.models.monitor_status import MonitorStatus, MonitorType
from core.core_constants import MOTHER_DB_PATH

MONITOR_NAME = "sonic_monitor"
DEFAULT_INTERVAL = 60  # fallback if nothing set in DB

CYCLONE_GROUP_LABEL = "cyclone_core"
CYCLONE_GROUPS = [
    "cyclone_engine",
    "Cyclone",
    "CycloneHedgeService",
    "CyclonePortfolioService",
    "CycloneAlertService",
    "CyclonePositionService",
    "PositionSyncService",
    "PositionCoreService",
    "PositionEnrichmentService",
    "AlertEvaluator",
    "AlertController",
    "AlertServiceManager",
    "DataLocker",
    "PriceSyncService",
    "DBCore",
    "Logger",
    "AlertUtils",
    "CalcServices",
    "LockerFactory",
    "HedgeManager",
    "CycleRunner",
    "ConsoleHelper",
]

_MONITOR_LABELS: Dict[MonitorType, str] = {
    MonitorType.SONIC: "Sonic",
    MonitorType.PRICE: "Price",
    MonitorType.POSITIONS: "Positions",
    MonitorType.XCOM: "XCom",
}


_MON_STATE: Dict[str, str] = {}


def _format_monitor_lines(status: Optional[MonitorStatus]) -> tuple[str, str]:
    if status is None:
        return "↑0/0/0", "–"

    pos_tokens: list[str] = []
    brief_tokens: list[str] = []
    for monitor_type, detail in status.monitors.items():
        label = _MONITOR_LABELS.get(monitor_type, monitor_type.value)
        state = getattr(detail.status, "value", str(detail.status))
        meta = detail.metadata if isinstance(getattr(detail, "metadata", None), dict) else {}
        skipped = bool(meta.get("skipped"))
        reason = str(meta.get("reason")) if meta.get("reason") else None
        token = "⏭" if skipped else state
        pos_tokens.append(f"{label}:{token}")
        last_dt = getattr(detail, "last_updated", None)
        last = last_dt.isoformat() if last_dt else "Never"
        if skipped and reason:
            brief_tokens.append(f"{label} → {token} ({reason}; {last})")
        elif skipped:
            brief_tokens.append(f"{label} → {token} ({last})")
        else:
            brief_tokens.append(f"{label} → {state} ({last})")

    pos_line = " • ".join(pos_tokens) if pos_tokens else "↑0/0/0"
    brief = " | ".join(brief_tokens) if brief_tokens else "–"
    return pos_line, brief


def _build_cycle_summary(
    cycle_num: int,
    elapsed: float,
    status: Optional[MonitorStatus],
    *,
    alerts_line: str,
    notifications: Optional[str] = None,
) -> Dict[str, Any]:
    pos_line, brief = _format_monitor_lines(status)
    notif = notifications or (status.sonic_last_complete if status else None)
    if notif:
        notif_line = f"Last sonic completion @ {notif}"
    else:
        notif_line = "NONE (no_breach)"

    summary = {
        "cycle_num": cycle_num,
        "elapsed_s": elapsed,
        "positions_line": pos_line,
        "positions_brief": brief,
        "alerts_inline": alerts_line,
        "notifications_brief": notif_line,
        "hedge_groups": 0,
    }

    summary["monitor_states_line"] = pos_line
    summary["monitor_brief"] = brief
    return summary


set_console_title("🦔 Sonic Monitor 🦔")

if os.getenv("SONIC_CONSOLE_LOGGER", "").strip().lower() not in {"1", "true", "on", "yes"}:
    _CONSOLE_REPORT = neuter_legacy_console_logger()
else:
    _CONSOLE_REPORT = {"present": False, "patched": [], "skipped": "ConsoleLogger enabled"}


def _to_iso(ts: Any) -> Optional[str]:
    if ts in (None, "", 0):
        return None
    try:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(float(ts), timezone.utc).isoformat()
        if isinstance(ts, str):
            try:
                return datetime.fromtimestamp(float(ts), timezone.utc).isoformat()
            except ValueError:
                # assume already iso-formatted
                datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return ts
    except Exception:
        return None
    return None


def _enrich_summary_from_locker(summary: Dict[str, Any], dl: DataLocker) -> None:
    try:
        prices = dl.prices.get_all_prices() if getattr(dl, "prices", None) else []
    except Exception:
        prices = []

    top_assets: list[str] = []
    prices_top3: list[tuple[str, float]] = []
    price_changes: Dict[str, bool] = {}
    price_ages: Dict[str, int] = {}
    latest_price_ts: Optional[str] = None

    if prices:
        # Deduplicate by asset_type preserving latest order
        seen = set()
        sorted_prices = sorted(
            prices,
            key=lambda row: float(row.get("last_update_time") or 0.0),
            reverse=True,
        )
        now_ts = datetime.now(timezone.utc).timestamp()
        for row in sorted_prices:
            asset = str(row.get("asset_type") or "").strip() or "UNKNOWN"
            if asset in seen:
                continue
            seen.add(asset)
            price = float(row.get("current_price") or 0.0)
            prices_top3.append((asset, price))
            top_assets.append(asset)

            last_ts = row.get("last_update_time")
            if latest_price_ts is None:
                latest_price_ts = _to_iso(last_ts)
            try:
                last_float = float(last_ts)
                price_ages[asset] = max(int((now_ts - last_float) // 60), 0)
            except Exception:
                pass

            prev = row.get("previous_price")
            try:
                price_changes[asset] = float(prev or 0.0) != float(price)
            except Exception:
                price_changes[asset] = False

            if len(prices_top3) >= 3:
                break

    if prices_top3:
        summary["prices_top3"] = prices_top3
        summary["assets_line"] = " ".join(top_assets)
    if price_changes:
        summary["price_changes"] = price_changes
    if price_ages:
        summary["price_ages"] = price_ages
    if latest_price_ts:
        summary["prices_updated_at"] = latest_price_ts

    # Hedge snapshot — count active hedge groups for console endcap
    try:
        hedge_mgr = getattr(dl, "hedges", None)
        if hedge_mgr:
            hedges = hedge_mgr.get_hedges() or []
            summary["hedge_groups"] = len(hedges)
    except Exception:
        pass

    # Positions snapshot
    try:
        positions = (
            dl.positions.get_all_positions() if getattr(dl, "positions", None) else []
        )
    except Exception:
        positions = []

    if positions:
        active = [p for p in positions if getattr(p, "status", "ACTIVE") != "CLOSED"]
        summary["positions_line"] = f"active {len(active)}/{len(positions)} total"

        # top 3 holdings summary
        def _fmt_position(p: Any) -> str:
            side = getattr(p, "position_type", "").upper() or "–"
            asset = getattr(p, "asset_type", "–")
            size = getattr(p, "size", 0)
            try:
                size_str = f"{float(size):.2f}" if isinstance(size, (int, float)) else str(size)
            except Exception:
                size_str = str(size)
            entry = getattr(p, "entry_price", 0)
            try:
                entry_str = f"{float(entry):.2f}" if isinstance(entry, (int, float)) else str(entry)
            except Exception:
                entry_str = str(entry)
            return f"{asset} {side} {size_str}@{entry_str}"

        try:
            top_positions = sorted(
                positions,
                key=lambda p: getattr(p, "last_updated", ""),
                reverse=True,
            )[:3]
        except Exception:
            top_positions = positions[:3]
        summary["positions_brief"] = " | ".join(_fmt_position(p) for p in top_positions)

        # Determine latest timestamp
        latest_ts: Optional[str] = None
        for pos in positions:
            ts = getattr(pos, "last_updated", None)
            iso = _to_iso(ts)
            if iso:
                if latest_ts is None or iso > latest_ts:
                    latest_ts = iso
        if latest_ts:
            summary["positions_updated_at"] = latest_ts



async def _run_monitor_tick(name: str, runner: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    key = f"mon_{name}"
    task_start(key, name)
    try:
        result = await asyncio.to_thread(runner, *args, **kwargs)
    except Exception as exc:
        task_end(key, "fail", note=str(exc))
        _MON_STATE[name] = "FAIL"
        raise
    else:
        if isinstance(result, dict) and result.get("skipped"):
            task_end(key, "skip", note="fresh")
            _MON_STATE[name] = "⏭"
        else:
            task_end(key, "ok")
            _MON_STATE[name] = "OK"
        return result

def get_monitor_interval(db_path=MOTHER_DB_PATH, monitor_name=MONITOR_NAME):
    dl = DataLocker(str(db_path))
    cursor = dl.db.get_cursor()
    if not cursor:
        logging.error("No DB cursor available; using default interval")
        return DEFAULT_INTERVAL
    cursor.execute(
        "SELECT interval_seconds FROM monitor_heartbeat WHERE monitor_name = ?",
        (monitor_name,),
    )
    row = cursor.fetchone()
    if row and row[0]:
        try:
            return int(row[0])
        except Exception:
            pass
    return DEFAULT_INTERVAL


def update_heartbeat(monitor_name, interval_seconds, db_path=MOTHER_DB_PATH):
    dl = DataLocker(str(db_path))
    cursor = dl.db.get_cursor()
    if not cursor:
        logging.error("No DB cursor available; heartbeat not recorded")
        return

    timestamp = datetime.now(timezone.utc).isoformat()
    cursor.execute(
        """
        INSERT INTO monitor_heartbeat (monitor_name, last_run, interval_seconds)
        VALUES (?, ?, ?)
        ON CONFLICT(monitor_name) DO UPDATE
            SET last_run = excluded.last_run,
                interval_seconds = excluded.interval_seconds
        """,
        (monitor_name, timestamp, interval_seconds),
    )
    dl.db.commit()


def write_ledger(status: str, metadata: dict | None = None, db_path=MOTHER_DB_PATH):
    dl = DataLocker(str(db_path))
    try:
        dl.ledger.insert_ledger_entry(MONITOR_NAME, status=status, metadata=metadata)
    except Exception as exc:  # pragma: no cover - log ledger failures
        logging.error(f"Failed to write ledger entry: {exc}")


def heartbeat(loop_counter: int):
    timestamp = datetime.now(timezone.utc).isoformat()
    logging.info("❤️ SonicMonitor heartbeat #%d at %s", loop_counter, timestamp)


async def sonic_cycle(loop_counter: int, cyclone: Cyclone):
    """Run a full Cyclone cycle and then execute enabled monitors."""
    logging.info("🔄 SonicMonitor cycle #%d starting", loop_counter)

    dl = DataLocker.get_instance()
    cfg = dl.system.get_var("sonic_monitor") or {}

    _MON_STATE.clear()

    if not cfg.get("enabled_sonic", True):
        logging.info("Sonic loop disabled via config")
        heartbeat(loop_counter)
        return

    # Execute the complete Cyclone pipeline
    await cyclone.run_cycle()

    # Run monitors based on config
    if cfg.get("enabled_market", True):

        await _run_monitor_tick("price_monitor", cyclone.monitor_core.run_by_name, "price_monitor")

        await _run_monitor_tick("market_monitor", cyclone.monitor_core.run_by_name, "market_monitor")
    if cfg.get("enabled_profit", True):
        await _run_monitor_tick("profit_monitor", cyclone.monitor_core.run_by_name, "profit_monitor")
    else:
        logging.info("Profit monitor disabled via configuration")
    # await asyncio.to_thread(cyclone.monitor_core.run_by_name, "risk_monitor")
    if cfg.get("enabled_liquid", True):
        await _run_monitor_tick("liquid_monitor", cyclone.monitor_core.run_by_name, "liquid_monitor")

    # Alert V2 pipeline disabled

    heartbeat(loop_counter)
    logging.info("✅ SonicMonitor cycle #%d complete", loop_counter)

    await notify_listeners()


def run_monitor(
    dl: Optional[DataLocker] = None,
    poll_interval_s: Optional[int] = None,
    cycles: Optional[int] = None,
) -> None:
    """Run the Sonic monitor console loop."""

    link_flag = os.getenv("SONIC_MONITOR_DASHBOARD_LINK", "1").strip().lower()
    if link_flag not in {"0", "false", "off", "no"}:
        host = os.getenv("SONIC_DASHBOARD_HOST", "127.0.0.1")
        route = os.getenv("SONIC_DASHBOARD_ROUTE", "/dashboard")
        port_env = os.getenv("SONIC_DASHBOARD_PORT", "5001")
        try:
            port = int(port_env)
        except ValueError:
            port = 5001
        emit_dashboard_link(host=host, port=port, route=route)

    # ── Top-of-screen env readout (path + Twilio) ─────────────────────────────
    try:
        env_path = os.getenv("SONIC_ENV_PATH_RESOLVED") or _env_used or "–"

        # Canonical first, then fall back to legacy/aliases
        sid = (
            os.getenv("TWILIO_SID")
            or os.getenv("TWILIO_ACCOUNT_SID")
            or "–"
        )
        from_ = (
            os.getenv("TWILIO_FROM")
            or os.getenv("TWILIO_FROM_PHONE")
            or "–"
        )
        to_ = (
            os.getenv("TWILIO_TO")
            or os.getenv("TWILIO_TO_PHONE")
            or os.getenv("TWILIO_DEFAULT_TO")
            or "–"
        )

        print(f"📦 .env (used): {env_path}")
        print(f"📞 Twilio (env): sid={sid[:3]}… • from={from_} • to={to_}")
    except Exception:
        pass

    install_strict_console_filter()
    muted = silence_legacy_console_loggers()
    try:
        emit_boot_status(muted, group_label="", groups=None)
    except Exception:
        logging.debug("emit_boot_status failed", exc_info=True)

    from backend.core.monitor_core.monitor_core import MonitorCore

    if dl is None:
        dl = DataLocker.get_instance(str(MOTHER_DB_PATH))
    else:
        # Ensure the provided locker is reused by singleton consumers
        setattr(DataLocker, "_instance", dl)

    display_interval = poll_interval_s or DEFAULT_INTERVAL
    emit_config_banner(dl, display_interval)

    # 1.5) one-time Pre-Launch Checklist (provenance + Twilio + monitor values)
    try:
        print_prelaunch_checklist(dl, display_interval)
    except Exception:
        pass

    monitor_core = MonitorCore()
    cyclone = Cyclone(monitor_core=monitor_core)

    cursor = dl.db.get_cursor()
    if not cursor:
        logging.error("No DB cursor available; cannot initialize heartbeat table")
        return
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS monitor_heartbeat (
            monitor_name TEXT PRIMARY KEY,
            last_run TIMESTAMP NOT NULL,
            interval_seconds INTEGER NOT NULL
        )
    """
    )
    dl.db.commit()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop_counter = 0
    cycle_limit = cycles if cycles is not None and cycles > 0 else None
    try:
        while cycle_limit is None or loop_counter < cycle_limit:
            interval = get_monitor_interval()
            if interval <= 0:
                interval = display_interval

            loop_counter += 1
            start_time = time.time()
            cycle_failed = False

            try:
                loop.run_until_complete(sonic_cycle(loop_counter, cyclone))
                update_heartbeat(MONITOR_NAME, interval)
                write_ledger("Success")
            except Exception as exc:  # pragma: no cover - runtime safety
                cycle_failed = True
                logging.exception("SonicMonitor cycle failure")
                write_ledger("Error", {"error": str(exc)})

            status_snapshot: Optional[MonitorStatus] = None
            try:
                status_snapshot = dl.ledger.get_monitor_status_summary()
                if hasattr(status_snapshot, "model_dump"):
                    payload = status_snapshot.model_dump()
                elif hasattr(status_snapshot, "dict"):
                    payload = status_snapshot.dict()
                else:
                    payload = status_snapshot
                logging.debug("Monitor status summary: %s", payload)
            except Exception:  # pragma: no cover - defensive logging
                logging.exception("Failed to update monitor status summary")

            elapsed = time.time() - start_time
            alerts_line = "fail 1/1 error" if cycle_failed else "pass 0/0 –"
            icon_line: Optional[str] = None
            try:
                db_manager = getattr(dl, "db", None)
                conn = None
                if db_manager is not None:
                    conn = getattr(db_manager, "conn", None) or db_manager.connect()
                icon_line = compute_positions_icon_line(conn)
            except Exception:
                logging.debug("positions icon line computation failed", exc_info=True)
            summary = _build_cycle_summary(
                loop_counter,
                elapsed,
                status_snapshot,
                alerts_line=alerts_line,
            )
            # Populate summary data directly from the DataLocker so the endcap has
            # fresh values even if later enrich steps fail.
            try:
                price_mgr = getattr(dl, "prices", None)
                if price_mgr:
                    price_rows = price_mgr.get_all_prices() or []
                    top3: list[tuple[str, float]] = []
                    seen_assets: set[str] = set()
                    latest_iso: Optional[str] = None
                    for row in price_rows:
                        asset = str(row.get("asset_type") or "").upper() or "UNKNOWN"
                        if asset in seen_assets:
                            continue
                        seen_assets.add(asset)
                        try:
                            price_val = float(row.get("current_price") or 0.0)
                        except Exception:
                            price_val = 0.0
                        top3.append((asset, price_val))
                        iso = _to_iso(row.get("last_update_time"))
                        if iso and (latest_iso is None or iso > latest_iso):
                            latest_iso = iso
                        if len(top3) >= 3:
                            break
                    if top3:
                        summary["prices_top3"] = top3
                    if latest_iso and not summary.get("prices_updated_at"):
                        summary["prices_updated_at"] = latest_iso
            except Exception:
                logging.debug("Failed to populate price summary", exc_info=True)
            try:
                positions_mgr = getattr(dl, "positions", None)
                if positions_mgr:
                    positions = positions_mgr.get_all_positions() or []
                    latest_iso: Optional[str] = None
                    for pos in positions:
                        iso = _to_iso(getattr(pos, "last_updated", None))
                        if iso and (latest_iso is None or iso > latest_iso):
                            latest_iso = iso
                    if latest_iso and not summary.get("positions_updated_at"):
                        summary["positions_updated_at"] = latest_iso
            except Exception:
                logging.debug("Failed to populate position summary", exc_info=True)
            try:
                hedge_mgr = getattr(dl, "hedges", None)
                if hedge_mgr:
                    hedges = hedge_mgr.get_hedges() or []
                    summary["hedge_groups"] = len(hedges)
            except Exception:
                logging.debug("Failed to populate hedge summary", exc_info=True)
            try:
                if _MON_STATE:
                    ordered_keys = (
                        "price_monitor",
                        "market_monitor",
                        "profit_monitor",
                        "liquid_monitor",
                        "position_monitor",
                    )
                    tokens: list[str] = []
                    for key in ordered_keys:
                        if key in _MON_STATE:
                            label = key.replace("_monitor", "")
                            tokens.append(f"{label}:{_MON_STATE[key]}")
                    if tokens:
                        summary["monitors_inline"] = " ".join(tokens)
            except Exception:
                pass
            try:
                _enrich_summary_from_locker(summary, dl)
            except Exception:
                logging.exception("Failed to enrich sonic summary")
            if icon_line:
                summary.setdefault("positions_icon_line", icon_line)
            cfg = {}
            try:
                cfg = dl.system.get_var("sonic_monitor") or {}
            except Exception:
                logging.debug("Failed to load sonic_monitor config", exc_info=True)

            emit_compact_cycle(
                summary,
                cfg,
                interval,
                enable_color=True,
            )

            sleep_time = max(interval - elapsed, 0)
            if sleep_time > 0:
                time.sleep(sleep_time)
    except KeyboardInterrupt:
        logging.info("SonicMonitor terminated by user.")
    finally:
        try:
            loop.close()
        except Exception:
            pass


if __name__ == "__main__":
    run_monitor()
