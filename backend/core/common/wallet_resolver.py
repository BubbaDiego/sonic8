# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from typing import Optional, List, Dict, Any

from backend.data.data_locker import DataLocker


def resolve_active_wallet(dl: DataLocker, override: Optional[str] = None) -> Optional[str]:
    """
    Resolve the active wallet public address without using system vars.

    Priority:
      1) explicit override (e.g., CLI/env for one-off runs)
      2) SONIC_ACTIVE_WALLET environment variable
      3) dl.wallets.get_wallets() → pick is_active=True row, else first row
    """
    if override and len(override) > 30:
        return override

    env = os.getenv("SONIC_ACTIVE_WALLET")
    if env and len(env) > 30:
        return env

    wmgr = getattr(dl, "wallets", None)
    if not wmgr:
        return None

    try:
        wallets: List[Dict[str, Any]] = wmgr.get_wallets() or []
    except Exception:
        return None

    # Prefer active wallet if present
    for w in wallets:
        if bool(w.get("is_active", False)):
            return w.get("public_address") or w.get("pubkey")

    # Fallback to first wallet if any
    if wallets:
        w0 = wallets[0]
        return w0.get("public_address") or w0.get("pubkey")

    return None
