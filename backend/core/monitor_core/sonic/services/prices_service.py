# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional

from backend.core.logging import log
from backend.core.monitor_core.monitor_service import MonitorService
from backend.data.data_locker import DataLocker


class PricesService:
    """High-level price synchronization helper for monitors and Cyclone."""

    def __init__(
        self,
        dl: DataLocker,
        cfg: Optional[Dict[str, Any]] = None,
        *,
        monitor_service: Optional[MonitorService] = None,
    ) -> None:
        if dl is None:
            raise ValueError("PricesService requires a DataLocker instance")
        self.dl = dl
        self.cfg = cfg or {}
        self.service = monitor_service or MonitorService()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _log_price_tick(self, asset_type: str, price: float, source: str) -> None:
        """Record a price tick in the learning DB (best-effort)."""
        try:
            logger_mod = importlib.import_module(
                "backend.data.learning_database.learning_event_logger"
            )
            logger_mod.log_learning_event(
                "price_ticks",
                {
                    "asset_type": asset_type,
                    "price": float(price),
                    "source": source,
                },
            )
        except Exception as exc:  # pragma: no cover - logging must not crash
            log.debug(
                f"Learning DB logging skipped for {asset_type}: {exc}",
                source="PricesService",
            )

    def _insert_price(self, asset_type: str, price: float, source: str) -> None:
        self.dl.insert_or_update_price(asset_type, float(price), source=source)

    def _normalize_prices(self, prices: Optional[Mapping[str, Any]]) -> Dict[str, float]:
        normalized: Dict[str, float] = {}
        if not prices:
            return normalized
        for asset, value in prices.items():
            if value in (None, ""):
                continue
            try:
                normalized[asset] = float(value)
            except (TypeError, ValueError):
                log.debug(
                    f"Skipping non-numeric price for {asset}: {value}",
                    source="PricesService",
                )
        return normalized

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def run_full_price_sync(self, *, source: str = "prices_service") -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "success": False,
            "source": source,
            "assets": {},
            "fetched_count": 0,
            "skipped_assets": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            fetched = self.service.fetch_prices()
        except Exception as exc:
            log.error(f"Failed to fetch prices: {exc}", source="PricesService")
            summary["error"] = str(exc)
            return summary

        normalized = self._normalize_prices(fetched)
        skipped = [asset for asset in (fetched or {}) if asset not in normalized]

        for asset, price in normalized.items():
            try:
                self._insert_price(asset, price, source)
                self._log_price_tick(asset, price, source)
                summary["assets"][asset] = price
            except Exception as exc:
                log.error(
                    f"Failed to persist price for {asset}: {exc}",
                    source="PricesService",
                )
                skipped.append(asset)

        summary["fetched_count"] = len(summary["assets"])
        summary["skipped_assets"] = skipped
        summary["success"] = True
        return summary

    def sync_prices(self, *, source: str = "prices_service") -> Dict[str, Any]:
        """Alias retained for backwards compatibility."""
        return self.run_full_price_sync(source=source)


def sync_prices_service(ctx: Any) -> Dict[str, Any]:
    """Adapter entry point for Sonic services."""
    dl = getattr(ctx, "dl", None)
    if dl is None:
        raise ValueError("Context object must expose a DataLocker via `ctx.dl`")
    cfg = getattr(ctx, "cfg", None)
    source = getattr(ctx, "source", "prices_service")
    service = PricesService(dl=dl, cfg=cfg)
    return service.run_full_price_sync(source=source)
