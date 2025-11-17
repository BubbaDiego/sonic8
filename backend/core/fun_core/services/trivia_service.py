
"""Fetch trivia questions."""
from datetime import datetime
from typing import Optional, Dict, Any
import html

from .base import BaseFunService
from ..models import FunContent, FunType

class TriviaService(BaseFunService):
    async def _fetch_remote(self) -> FunContent:
        tc = await self._try_open_trivia()
        if tc:
            return tc
        tc = await self._try_jservice()
        if tc:
            return tc
        raise RuntimeError("Trivia providers failed")

    async def _try_open_trivia(self) -> Optional[FunContent]:
        url = "https://opentdb.com/api.php?amount=1&type=boolean"
        r = await self._request("GET", url)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("response_code") != 0:
            return None
        q = data["results"][0]
        question = html.unescape(q["question"])
        answer = html.unescape(q["correct_answer"])
        return FunContent(
            type=FunType.trivia,
            text=question,
            source="Open Trivia DB",
            fetched_at=datetime.utcnow(),
            extra={"answer": answer, "difficulty": q.get("difficulty")},
        )

    async def _try_jservice(self) -> Optional[FunContent]:
        url = "http://jservice.io/api/random"
        r = await self._request("GET", url)
        if r.status_code != 200:
            return None
        j = r.json()[0]
        return FunContent(
            type=FunType.trivia,
            text=j["question"],
            source="jService",
            fetched_at=datetime.utcnow(),
            extra={"answer": j["answer"], "category": j.get("category")},
        )
