from __future__ import annotations

from typing import Optional, Dict, Any, Tuple

try:
    from backend.data.data_locker import DataLocker  # type: ignore
except Exception:
    DataLocker = None  # type: ignore

PRIMARY_KEY = "monitor_config.sonic"   # new canonical location
LEGACY_KEY  = "sonic_monitor"          # legacy key we still update until hard pivot


def read_config() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Read from DataLocker.system; prefer PRIMARY_KEY, then LEGACY_KEY."""
    if DataLocker is None:
        return None, None
    try:
        dl = DataLocker.get_instance()
        sysm = getattr(dl, "system", None)
        if not sysm or not hasattr(sysm, "get_var"):
            return None, None

        cfg = sysm.get_var(PRIMARY_KEY)
        if cfg:
            return cfg, PRIMARY_KEY

        cfg = sysm.get_var(LEGACY_KEY)
        if cfg:
            return cfg, LEGACY_KEY

        return None, PRIMARY_KEY
    except Exception:
        return None, PRIMARY_KEY


def write_config(cfg: Dict[str, Any], also_write_legacy: bool = True) -> Tuple[bool, Optional[str]]:
    """Write to PRIMARY_KEY and (optionally) mirror to LEGACY_KEY until you say to stop."""
    if DataLocker is None:
        return False, None
    try:
        dl = DataLocker.get_instance()
        sysm = getattr(dl, "system", None)
        if not sysm or not hasattr(sysm, "set_var"):
            return False, None

        sysm.set_var(PRIMARY_KEY, cfg)
        if also_write_legacy:
            sysm.set_var(LEGACY_KEY, cfg)
        return True, PRIMARY_KEY
    except Exception:
        return False, PRIMARY_KEY
