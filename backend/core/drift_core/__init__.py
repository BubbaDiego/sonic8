from __future__ import annotations

"""
Drift core package for Sonic.

This package contains the building blocks required to integrate the
Drift Protocol (perpetuals on Solana) into Sonic.
"""

from .drift_core import DriftCore
from .drift_core_service import DriftCoreService

__all__ = ["DriftCore", "DriftCoreService"]
