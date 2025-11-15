# -*- coding: utf-8 -*-
"""
MarketMonitor (stub)

This module is a temporary stub while the real market monitor / market_core
implementation is being developed on another branch.

The original interface exposed a `MarketMonitor` class with methods that
produced monitor status rows. To maintain import compatibility, we keep a
minimal class with `run` / `run_once` methods that return an empty status
payload.
"""

from __future__ import annotations

from typing import Any, Dict, List


class MarketMonitor:
    """
    Stubbed MarketMonitor.

    Methods:
        run(dl, cfg)      -> dict
        run_once(dl, cfg) -> dict

    Both methods return the same structure:
        {
            "ok": True,
            "statuses": [],
            "note": "market monitor stubbed (no-op in sonic8 main)",
        }
    """

    @classmethod
    def run(cls, dl: Any, cfg: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return cls.run_once(dl, cfg or {})

    @classmethod
    def run_once(cls, dl: Any, cfg: Dict[str, Any] | None = None) -> Dict[str, Any]:
        # `dl` (DataLocker) and `cfg` are accepted for API compatibility only.
        statuses: List[Dict[str, Any]] = []
        return {
            "ok": True,
            "statuses": statuses,
            "note": "market monitor stubbed (no-op in sonic8 main)",
        }
