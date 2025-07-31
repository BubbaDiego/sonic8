
"""Registry mapping FunType to service instances."""
import asyncio
from typing import Dict

from .models import FunType
from .services.joke_service import JokeService
from .services.trivia_service import TriviaService
from .services.quote_service import QuoteService

class FunRegistry:
    _services: Dict[FunType, object] = {
        FunType.joke: JokeService(),
        FunType.trivia: TriviaService(),
        FunType.quote: QuoteService(),
    }

    @classmethod
    def by_type(cls, t: FunType):
        return cls._services[t]
