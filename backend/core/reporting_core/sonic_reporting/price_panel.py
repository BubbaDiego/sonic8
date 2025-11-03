"""Console price panel shim.

This module provides the Sonic "price panel" renderer while keeping
compatibility with the existing ``positions_core_adapter`` implementation.
It exposes a ``render`` function that proxies to the adapter's renderer so
callers can import ``price_panel`` directly.
"""
from __future__ import annotations

from typing import Any, Dict

from .positions_core_adapter import render as _render_prices

__all__ = ["render"]


def render(csum: Dict[str, Any], *, dl: Any = None) -> None:
    """Render the prices panel using the adapter implementation."""
    _render_prices(csum, dl=dl)
