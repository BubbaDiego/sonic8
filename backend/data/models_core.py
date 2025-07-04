"""Compatibility exports for data models used by DataLocker."""

from backend.models.alert_thresholds import AlertThreshold
from backend.models.system_data import SystemVariables

__all__ = ["AlertThreshold", "SystemVariables"]
