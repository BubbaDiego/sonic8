"""
Abstract request definition for AutoCore.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class AutoRequest(ABC):
    """Every AutoCore request must implement the *async* ``execute`` method."""

    @abstractmethod
    async def execute(self) -> Dict[str, Any]:
        """Run the request and return a JSON‑serialisable dict."""
