# -*- coding: utf-8 -*-
"""
Sonic8 — Market monitor (stub)

This file temporarily stubs out the market monitor logic while the real
market_core / market monitor implementation is developed in another branch.

The Sonic monitor engine imports `run_market_monitors(ctx)` via
`backend.core.monitor_core.sonic.registry.DEFAULT_MONITORS`, so this
function must be present and return a dict.

Contract:
    • Returns a dict with at least:
        - "ok": bool
        - "statuses": list[dict]
        - "note": str (optional)
    • The engine will treat an empty `statuses` list as "no alerts".
"""

from __future__ import annotations

from typing import Any, Dict, List


def run_market_monitors(ctx: Any) -> Dict[str, Any]:
    """
    Stubbed market monitor runner.

    The real implementation will eventually evaluate broader market
    conditions (volatility, index moves, macro triggers, etc.) and emit
    MonitorStatus rows.

    For now we simply return an empty status list so:
      • the Sonic monitor's "Market" row remains in the Cycle Activity panel
      • no DB writes or external calls are performed
    """
    # ctx is a MonitorContext but we intentionally do not use it here
    statuses: List[Dict[str, Any]] = []

    return {
        "ok": True,
        "statuses": statuses,
        "note": "market monitor stubbed (no-op in sonic8 main)",
    }
