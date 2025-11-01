"""
Test bootstrap:
 - Ensure repo root and backend are on sys.path
 - Provide import aliases so legacy tests like `from positions.position_core import PositionCore`
   resolve to `backend.core.positions_core.position_core`, etc.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path


# Put repo root and backend on sys.path
ROOT = Path(__file__).resolve().parents[1]   # .../sonic7
BACKEND = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


# Map legacy short names -> current backend packages
# Extend as needed if tests reference other legacy namespaces.
ALIASES = {
    # data.alert -> backend.models.alert
    "data": "backend.models",
    # positions.position_core -> backend.core.positions_core.position_core
    "positions": "backend.core.positions_core",
    # wallets.wallet_core -> backend.core.wallet_core.wallet_core
    "wallets": "backend.core.wallet_core",
    # monitor.* -> backend.core.monitor_core.*
    "monitor": "backend.core.monitor_core",
    # xcom.* -> backend.core.xcom_core.*
    "xcom": "backend.core.xcom_core",
    # trader_core.* -> backend.core.trader_core.*
    "trader_core": "backend.core.trader_core",
    # legacy app.* blueprints -> backend.* modules
    "app": "backend",
}


def _alias_package(alias: str, target_pkg: str) -> None:
    """
    Install a package-level alias so 'import {alias}.sub' resolves under target_pkg's __path__.
    """
    try:
        pkg = importlib.import_module(target_pkg)
    except Exception:
        return
    # Only set if not already present, to avoid masking real packages during dev.
    if alias not in sys.modules:
        sys.modules[alias] = pkg


def pytest_sessionstart(session):
    for name, target in ALIASES.items():
        _alias_package(name, target)
