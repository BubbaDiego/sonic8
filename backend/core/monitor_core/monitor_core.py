import sys
import os
from typing import Optional
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from core.logging import log

# Import your monitor classes here
from backend.core.monitor_core.price_monitor import PriceMonitor
from backend.core.monitor_core.position_monitor import PositionMonitor
from backend.core.monitor_core.operations_monitor import OperationsMonitor
from backend.core.monitor_core.xcom_monitor import XComMonitor
from backend.core.monitor_core.twilio_monitor import TwilioMonitor
from backend.core.monitor_core.profit_monitor import ProfitMonitor  # Added ProfitMonitor
from backend.core.monitor_core.risk_monitor import RiskMonitor
#from backend.core.monitor_core.oracle_monitor.oracle_monitor import OracleMonitor
from backend.core.monitor_core.monitor_registry import MonitorRegistry
from backend.core.locker_factory import get_locker

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
            self.registry.register("operations_monitor", OperationsMonitor())
            self.registry.register("xcom_monitor", XComMonitor())
            self.registry.register("twilio_monitor", TwilioMonitor())
            self.registry.register("profit_monitor", ProfitMonitor())  # Registered ProfitMonitor
            self.registry.register("risk_monitor", RiskMonitor())
#            self.registry.register("oracle_monitor", OracleMonitor())

    def run_all(self):
        """
        Run all registered monitors in sequence.
        """
        for name, monitor in self.registry.get_all_monitors().items():
            try:
                log.info(f"Running monitor: {name}", source="MonitorCore")
                monitor.run_cycle()
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
                monitor.run_cycle()
                log.success(f"Monitor '{name}' completed successfully.", source="MonitorCore")
            except Exception as e:
                log.error(f"Monitor '{name}' failed: {e}", source="MonitorCore")
        else:
            log.warning(f"Monitor '{name}' not found.", source="MonitorCore")

    def get_status_snapshot(self):
        """Return the current monitor health summary."""

        dl = get_locker()
        return dl.ledger.get_monitor_status_summary()
