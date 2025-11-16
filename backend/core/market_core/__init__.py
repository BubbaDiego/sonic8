# backend/core/market_core/__init__.py
"""
Market Core package.

Modern usage is via the functional API:

    from backend.core.market_core.market_engine import evaluate_market_alerts

We intentionally do *not* re-export the legacy MarketCore class here anymore,
to avoid importing the old market_core.py module that depended on
PriceAlertConfig / PriceAlertState, which have been removed in sonic8.
"""

from .market_engine import evaluate_market_alerts

__all__ = ["evaluate_market_alerts"]
