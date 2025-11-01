"""
Bootstraps test imports so the Launch Pad → Topic Test Runner can collect tests
without blowing up on legacy short import paths.
"""
from __future__ import annotations
import sys, importlib, types
from pathlib import Path

# ---------------------------------------------------------------------------
# Put repo root and backend on sys.path
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]   # .../sonic7
BACKEND = ROOT / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# ---------------------------------------------------------------------------
# Helpers to alias modules / packages
# ---------------------------------------------------------------------------
def alias_package(alias: str, target_pkg: str) -> None:
    """Register an existing package under a new top-level name."""
    try:
        pkg = importlib.import_module(target_pkg)
    except Exception:
        return
    sys.modules.setdefault(alias, pkg)

def alias_module(alias_fqn: str, target_fqn: str) -> None:
    """Register a specific module under an alias (fully-qualified)."""
    try:
        mod = importlib.import_module(target_fqn)
    except Exception:
        return
    sys.modules.setdefault(alias_fqn, mod)

def ensure_twilio_shim():
    """
    Provide a minimal shim for `notifications.twilio_sms_sender` so imports succeed.
    If an xcom SMS service exists, delegate to it; otherwise no-op.
    """
    name = "notifications.twilio_sms_sender"
    if name in sys.modules:
        return
    mod = types.ModuleType(name)
    try:
        xs = importlib.import_module("backend.core.xcom_core.sms_service")
    except Exception:
        xs = None

    class TwilioSMSSender:
        def __init__(self, *_, **__):
            self._impl_cls = None
            if xs is not None:
                # Try a few likely names
                self._impl_cls = getattr(xs, "SMSService", None) or getattr(xs, "SMSSender", None)

        def send(self, to: str, body: str):
            # Best-effort delegate; otherwise no-op success to keep unrelated topic runs green.
            if self._impl_cls:
                inst = self._impl_cls()
                send = getattr(inst, "send_sms", None) or getattr(inst, "send", None)
                if callable(send):
                    return send(to, body)
            return True

    mod.TwilioSMSSender = TwilioSMSSender
    sys.modules[name] = mod

# ---------------------------------------------------------------------------
# Main alias map
# ---------------------------------------------------------------------------
ALIASED_PACKAGES = {
    # legacy short names → actual packages
    "positions":   "backend.core.positions_core",
    "wallets":     "backend.core.wallet_core",
    "monitor":     "backend.core.monitor_core",
    "xcom":        "backend.core.xcom_core",
    "trader_core": "backend.core.trader_core",
    "app":         "backend",
    # helpful base for data.* imports (we override key submodules below)
    "data":        "backend.data",
}

# Specific module-level aliases where tests expect different layout
ALIASED_MODULES = {
    # tests import `from data.data_locker import DataLocker`
    "data.data_locker": "backend.data.data_locker",
    # tests import `from data.dl_wallets import ...`
    "data.dl_wallets":  "backend.data.dl_wallets",
    # tests import `from data.dl_hedges import ...`
    "data.dl_hedges":   "backend.data.dl_hedges",
    # tests import `from data.alert import ...` but model lives under backend.models
    "data.alert":       "backend.models.alert",
}

def pytest_sessionstart(session):
    # Install package-level aliases
    for alias, target in ALIASED_PACKAGES.items():
        alias_package(alias, target)
    # Install specific module redirects
    for alias, target in ALIASED_MODULES.items():
        alias_module(alias, target)
    # Provide Twilio shim (keeps unrelated topics from failing during import)
    ensure_twilio_shim()
