
"""Abstract base class for all Fun services."""
from __future__ import annotations
import random, asyncio, logging
from abc import ABC, abstractmethod
from datetime import datetime
from cachetools import TTLCache
import httpx

from ..models import FunContent

_log = logging.getLogger("fun_core")

class BaseFunService(ABC):
    """Common helper – handles httpx client + simple TTL cache."""

    def __init__(self, ttl_seconds: int = 900, max_cache: int = 128):
        self._cache = TTLCache(maxsize=max_cache, ttl=ttl_seconds)
        self._client = httpx.AsyncClient(
            timeout=5.0,
            headers={
                "User-Agent": "fun_core/1.0 (+https://github.com/sonic1/fun_core)"
            },
        )

    async def get_random(self) -> FunContent:
        """Return a fresh FunContent, falling back to cache on error."""
        try:
            content = await self._fetch_remote()
            self._cache[content.fetched_at.timestamp()] = content
            return content
        except Exception as exc:  # noqa: BLE001
            _log.warning("Remote fetch failed: %s", exc, exc_info=True)
            # random cache fallback
            if len(self._cache):
                return random.choice(list(self._cache.values()))
            raise  # re‑raise if no cache

    @abstractmethod
    async def _fetch_remote(self) -> FunContent:
        """Subclass must implement one remote fetch attempt."""
        raise NotImplementedError
