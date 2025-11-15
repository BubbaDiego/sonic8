import sys
from typing import Optional
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from core.logging import log
from backend.models.monitor_status import MonitorStatus
from backend.data.dl_monitor_ledger import DLMonitorLedgerManager
from data.data_locker import DataLocker

# Import your monitor classes here
from backend.core.monitor_core.price_monitor import PriceMonitor
from backend.core.monitor_core.position_monitor import PositionMonitor
try:
    from backend.core.monitor_core.operations_monitor import OperationsMonitor
except Exception:
    OperationsMonitor = None  # type: ignore[assignment]
from backend.core.monitor_core.xcom_monitor import XComMonitor
from backend.core.monitor_core.twilio_monitor import TwilioMonitor
from backend.core.monitor_core.profit_monitor import ProfitMonitor  # Added ProfitMonitor
from backend.core.monitor_core.risk_monitor import RiskMonitor
# NEW →
from backend.core.monitor_core.liquidation_monitor import LiquidationMonitor
from backend.core.monitor_core.market_monitor import MarketMonitor
#from backend.core.monitor_core.oracle_monitor.oracle_monitor import OracleMonitor
from backend.core.monitor_core.monitor_registry import MonitorRegistry


class MonitorCore:
    """Central controller for all registered monitors."""

    def __init__(self, registry: Optional[MonitorRegistry] = None):
        """Create the core controller.

        If ``registry`` is not supplied a new :class:`MonitorRegistry` instance
        is created and the default monitors are registered. When a registry is
        provided it is used as-is, allowing external callers to customize the
        available monitors.
        """

        self.registry = registry or MonitorRegistry()

        if registry is None:
            # Register default monitors when no custom registry is supplied
            self.registry.register("price_monitor", PriceMonitor())
            self.registry.register("position_monitor", PositionMonitor())
            if OperationsMonitor is not None:
                self.registry.register("operations_monitor", OperationsMonitor())
            self.registry.register("xcom_monitor", XComMonitor())
            self.registry.register("twilio_monitor", TwilioMonitor())
            self.registry.register("profit_monitor", ProfitMonitor())  # Registered ProfitMonitor
            self.registry.register("risk_monitor", RiskMonitor())
            self.registry.register("liquid_monitor", LiquidationMonitor())

            self.registry.register("market_monitor", MarketMonitor())
#            self.registry.register("oracle_monitor", OracleMonitor())

    def run_all(self):
        """
        Run all registered monitors in sequence.
        """
        for name, monitor in self.registry.get_all_monitors().items():
            try:
                log.info(f"Running monitor: {name}", source="MonitorCore")
                result = monitor.run_cycle()
                if isinstance(result, dict) and result.get("skipped"):
                    log.info(f"Monitor '{name}' skipped (fresh data).", source="MonitorCore")
                else:
                    log.success(f"Monitor '{name}' completed successfully.", source="MonitorCore")
            except Exception as e:
                log.error(f"Monitor '{name}' failed: {e}", source="MonitorCore")

    def run_by_name(self, name: str):
        """
        Run a specific monitor by its registered name.
        """
        monitor = self.registry.get(name)
        if monitor:
            try:
                log.info(f"Running monitor: {name}", source="MonitorCore")
                result = monitor.run_cycle()
                if isinstance(result, dict) and result.get("skipped"):
                    log.info(f"Monitor '{name}' skipped (fresh data).", source="MonitorCore")
                else:
                    log.success(f"Monitor '{name}' completed successfully.", source="MonitorCore")
                return result
            except Exception as e:
                log.error(f"Monitor '{name}' failed: {e}", source="MonitorCore")
        else:
            log.warning(f"Monitor '{name}' not found.", source="MonitorCore")

    def get_status_snapshot(self) -> MonitorStatus:
        """Return current monitor health snapshot from the ledger."""
        dl = DataLocker.get_instance()
        ledger = DLMonitorLedgerManager(dl.db)
        return ledger.get_monitor_status_summary()

