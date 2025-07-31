
"""Fetch jokes from public joke APIs."""
from datetime import datetime
from typing import Optional
import httpx, asyncio

from .base import BaseFunService
from ..models import FunContent, FunType

class JokeService(BaseFunService):
    async def _fetch_remote(self) -> FunContent:
        # Attempt JokeAPI
        text = await self._try_jokeapi()
        if text:
            return FunContent(
                type=FunType.joke,
                text=text,
                source="JokeAPI",
                fetched_at=datetime.utcnow(),
            )

        # Attempt Official Joke API
        text = await self._try_official_joke()
        if text:
            return FunContent(
                type=FunType.joke,
                text=text,
                source="Official Joke API",
                fetched_at=datetime.utcnow(),
            )

        # Fallback Dad Joke
        text = await self._try_dad_joke()
        if text:
            return FunContent(
                type=FunType.joke,
                text=text,
                source="icanhazdadjoke",
                fetched_at=datetime.utcnow(),
            )

        raise RuntimeError("All joke providers failed")

    async def _try_jokeapi(self) -> Optional[str]:
        url = "https://v2.jokeapi.dev/joke/Any"
        r = await self._client.get(url)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("type") == "single":
            return data.get("joke")
        return f"{data.get('setup')} {data.get('delivery')}"

    async def _try_official_joke(self) -> Optional[str]:
        url = "https://official-joke-api.appspot.com/random_joke"
        r = await self._client.get(url)
        if r.status_code != 200:
            return None
        jd = r.json()
        return f"{jd.get('setup')} {jd.get('punchline')}"

    async def _try_dad_joke(self) -> Optional[str]:
        url = "https://icanhazdadjoke.com/"
        r = await self._client.get(url, headers={**self._client.headers, "Accept": "application/json"})
        if r.status_code != 200:
            return None
        return r.json().get("joke")
