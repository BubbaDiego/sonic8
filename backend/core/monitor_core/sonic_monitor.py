import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

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
from backend.core.reporting_core.console_lines import emit_compact_cycle
from backend.core.reporting_core.console_reporter import (
    emit_boot_status,
    emit_dashboard_link,
    install_strict_console_filter,
    neuter_legacy_console_logger,
    silence_legacy_console_loggers,
)
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


def _format_monitor_lines(status: Optional[MonitorStatus]) -> tuple[str, str]:
    if status is None:
        return "↑0/0/0", "–"

    pos_tokens = []
    brief_tokens = []
    for monitor_type, detail in status.monitors.items():
        label = _MONITOR_LABELS.get(monitor_type, monitor_type.value)
        state = getattr(detail.status, "value", str(detail.status))
        pos_tokens.append(f"{label}:{state}")
        last = detail.last_updated.isoformat() if getattr(detail, "last_updated", None) else "Never"
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

    return {
        "cycle_num": cycle_num,
        "elapsed_s": elapsed,
        "positions_line": pos_line,
        "positions_brief": brief,
        "alerts_inline": alerts_line,
        "notifications_brief": notif_line,
        "hedge_groups": 0,
    }


set_console_title("🦔 Sonic Monitor 🦔")

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

    if not cfg.get("enabled_sonic", True):
        logging.info("Sonic loop disabled via config")
        heartbeat(loop_counter)
        return

    # Execute the complete Cyclone pipeline
    await cyclone.run_cycle()

    # Run monitors based on config
    if cfg.get("enabled_market", True):

        await asyncio.to_thread(cyclone.monitor_core.run_by_name, "price_monitor")

        await asyncio.to_thread(cyclone.monitor_core.run_by_name, "market_monitor")
    if cfg.get("enabled_profit", True):
        await asyncio.to_thread(cyclone.monitor_core.run_by_name, "profit_monitor")
    else:
        logging.info("Profit monitor disabled via configuration")
    # await asyncio.to_thread(cyclone.monitor_core.run_by_name, "risk_monitor")
    if cfg.get("enabled_liquid", True):
        await asyncio.to_thread(cyclone.monitor_core.run_by_name, "liquid_monitor")

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

    neuter_legacy_console_logger()

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

    install_strict_console_filter()
    muted = silence_legacy_console_loggers()
    emit_boot_status(muted, group_label=CYCLONE_GROUP_LABEL, groups=CYCLONE_GROUPS)

    from backend.core.monitor_core.monitor_core import MonitorCore

    if dl is None:
        dl = DataLocker.get_instance(str(MOTHER_DB_PATH))
    else:
        # Ensure the provided locker is reused by singleton consumers
        setattr(DataLocker, "_instance", dl)

    display_interval = poll_interval_s or DEFAULT_INTERVAL
    emit_config_banner(dl, display_interval)

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
    enable_color = sys.stdout.isatty()

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
                logging.debug(
                    "Monitor status summary: %s",
                    status_snapshot.dict() if hasattr(status_snapshot, "dict") else status_snapshot,
                )
            except Exception:  # pragma: no cover - defensive logging
                logging.exception("Failed to update monitor status summary")

            elapsed = time.time() - start_time
            alerts_line = "fail 1/1 error" if cycle_failed else "pass 0/0 –"
            summary = _build_cycle_summary(
                loop_counter,
                elapsed,
                status_snapshot,
                alerts_line=alerts_line,
            )
            emit_compact_cycle(summary, {}, interval, enable_color=enable_color)

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
