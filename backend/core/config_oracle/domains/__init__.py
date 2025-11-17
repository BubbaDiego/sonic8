# backend/core/config_oracle/domains/__init__.py
from __future__ import annotations

"""
Domain-specific helpers for the Config Oracle.

Each submodule here knows how to interpret raw config for a particular
domain (monitors, wallet, perps, etc.) and convert it into the typed
models defined in backend.core.config_oracle.models.
"""

from .monitor_limits import build_monitor_bundle_from_raw
from .xcom_config import build_xcom_config_from_raw

__all__ = ["build_monitor_bundle_from_raw", "build_xcom_config_from_raw"]
