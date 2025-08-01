"""Minimal orchestrator for Auto Core requests."""
from typing import Any, Dict
from .requests.base import AutoRequest

class AutoCore:
    """Runs a single AutoRequest instance and returns its result."""

    async def run(self, request: AutoRequest) -> Dict[str, Any]:
        return await request.execute()
