from abc import ABC, abstractmethod
from typing import Any, Dict

class AutoRequest(ABC):
    """Abstract base class for all Auto Core request types."""

    @abstractmethod
    async def execute(self) -> Dict[str, Any]:
        """Run the request and return a JSON‑serialisable result."""
        ...
