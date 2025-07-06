# monitor_status.py
# Author: BubbaDiego
# 📌 Purpose: Defines the MonitorStatus model for tracking backend monitor statuses and freshness.

from datetime import datetime
from enum import Enum
from typing import Dict, Optional
try:
    from pydantic import BaseModel, Field
    if not hasattr(BaseModel, "__fields__"):
        raise ImportError("stub")
except Exception:  # pragma: no cover - optional dependency or stub detected
    class BaseModel:  # type: ignore
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

        def dict(self) -> dict:  # type: ignore[override]
            return self.__dict__

    def Field(default=None, default_factory=None, **_):  # type: ignore
        if default_factory is not None:
            return default_factory()
        return default

class MonitorType(str, Enum):
    SONIC = "Sonic Monitoring"
    PRICE = "Price Monitoring"
    POSITIONS = "Positions Monitoring"
    XCOM = "XCom Communication"

class MonitorHealth(str, Enum):
    HEALTHY = "Healthy"
    WARNING = "Warning"
    ERROR = "Error"
    OFFLINE = "Offline"

class MonitorDetail(BaseModel):
    """
    📌 Represents details of an individual monitor, including its status and last update timestamp.
    """
    status: MonitorHealth = Field(..., description="Current health status of the monitor")
    last_updated: Optional[datetime] = Field(None, description="Timestamp of the last successful update")
    metadata: Optional[Dict] = Field(default_factory=dict, description="Additional contextual metadata")

class MonitorStatus(BaseModel):
    """
    📌 Comprehensive status snapshot of all system monitors.
    """
    monitors: Dict[MonitorType, MonitorDetail] = Field(
        default_factory=lambda: {
            MonitorType.SONIC: MonitorDetail(status=MonitorHealth.OFFLINE),
            MonitorType.PRICE: MonitorDetail(status=MonitorHealth.OFFLINE),
            MonitorType.POSITIONS: MonitorDetail(status=MonitorHealth.OFFLINE),
            MonitorType.XCOM: MonitorDetail(status=MonitorHealth.OFFLINE)
        },
        description="Current status of all monitored backend components"
    )

    def update_monitor(self, monitor_type: MonitorType, status: MonitorHealth, metadata: Dict = None):
        """
        ✅ Update a monitor's status and timestamp.

        Args:
            monitor_type (MonitorType): The specific monitor to update.
            status (MonitorHealth): The new status of the monitor.
            metadata (dict, optional): Any additional information to record.
        """
        self.monitors[monitor_type] = MonitorDetail(
            status=status,
            last_updated=datetime.utcnow(),
            metadata=metadata or {}
        )

    def get_monitor_status(self, monitor_type: MonitorType) -> MonitorDetail:
        """
        📖 Retrieve the current status details for a specific monitor.

        Args:
            monitor_type (MonitorType): The monitor whose status is requested.

        Returns:
            MonitorDetail: Status detail object.
        """
        return self.monitors.get(monitor_type, MonitorDetail(status=MonitorHealth.OFFLINE))

    def to_frontend_payload(self) -> Dict:
        """
        🌐 Formats the monitor status into a payload suitable for frontend display.

        Returns:
            dict: Frontend-friendly representation of the monitor statuses.
        """
        return {
            monitor.value: {
                "status": detail.status.value,
                "last_updated": detail.last_updated.isoformat() if detail.last_updated else "Never",
                "metadata": detail.metadata
            } for monitor, detail in self.monitors.items()
        }
