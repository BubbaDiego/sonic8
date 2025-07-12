"""Utility service to refresh Trader metrics when wallet balances change."""

from __future__ import annotations

from typing import Iterable

from backend.core.logging import log
from backend.core.trader_core.trader_core import TraderCore


class TraderUpdateService:
    """Refresh persisted Trader objects from updated wallet data."""

    def __init__(self, data_locker):
        self.dl = data_locker
        self.core = TraderCore(data_locker)

    # ------------------------------------------------------------------
    def _refresh_names(self, names: Iterable[str]) -> int:
        count = 0
        for name in names:
            try:
                if getattr(self.dl, "traders", None):
                    existing = self.dl.traders.get_trader_by_name(name)
                    if existing:
                        self.core.store.save(existing)
                self.core.refresh_trader(name)
                log.info(
                    f"🔄 Trader refreshed: {name}",
                    source="TraderUpdateService",
                )
                count += 1
            except Exception as exc:  # pragma: no cover - just log
                log.error(
                    f"Failed to refresh trader {name}: {exc}",
                    source="TraderUpdateService",
                )
        return count

    def refresh_trader_for_wallet(self, wallet_name: str) -> int:
        """Refresh trader(s) whose wallet matches ``wallet_name``."""
        if not getattr(self.dl, "traders", None):
            log.debug(
                "No trader manager available; skipping trader refresh",
                source="TraderUpdateService",
            )
            return 0
        try:
            traders = self.dl.traders.list_traders()
        except Exception as exc:  # pragma: no cover - just log
            log.error(
                f"Failed to list traders: {exc}",
                source="TraderUpdateService",
            )
            return 0
        names = [t.name for t in traders if getattr(t, "wallet", None) == wallet_name]
        return self._refresh_names(names)

    def refresh_all_traders(self) -> int:
        """Refresh all traders stored in ``DataLocker``."""
        if not getattr(self.dl, "traders", None):
            log.debug(
                "No trader manager available; skipping trader refresh",
                source="TraderUpdateService",
            )
            return 0
        try:
            names = [t.name for t in self.dl.traders.list_traders()]
        except Exception as exc:  # pragma: no cover - just log
            log.error(
                f"Failed to list traders: {exc}",
                source="TraderUpdateService",
            )
            return 0
        return self._refresh_names(names)
