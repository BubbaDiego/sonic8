
"""Fetch inspirational quotes from public APIs."""
from datetime import datetime
from typing import Optional

from .base import BaseFunService
from ..models import FunContent, FunType

class QuoteService(BaseFunService):
    async def _fetch_remote(self) -> FunContent:
        qc = await self._try_zenquotes()
        if qc:
            return qc
        qc = await self._try_quotable()
        if qc:
            return qc
        raise RuntimeError("Quote providers failed")

    async def _try_zenquotes(self) -> Optional[FunContent]:
        url = "https://zenquotes.io/api/random"
        r = await self._client.get(url)
        if r.status_code != 200:
            return None
        data = r.json()[0]
        text = f"{data['q']} — {data['a']}"
        return FunContent(
            type=FunType.quote,
            text=text,
            source="ZenQuotes",
            fetched_at=datetime.utcnow(),
        )

    async def _try_quotable(self) -> Optional[FunContent]:
        url = "https://api.quotable.io/random"
        r = await self._client.get(url)
        if r.status_code != 200:
            return None
        d = r.json()
        text = f"{d['content']} — {d['author']}"
        return FunContent(
            type=FunType.quote,
            text=text,
            source="Quotable",
            fetched_at=datetime.utcnow(),
        )
