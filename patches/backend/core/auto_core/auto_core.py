"""
Minimal AutoCore orchestrator.
"""
from typing import Any, Dict
from .requests.base import AutoRequest


class AutoCore:
    """
    Simple orchestrator that executes exactly one AutoRequest and returns the
    result. This is *deliberately* minimal for v1; add batching, persistence,
    or retries at higher layers once this stabilises.
    """

    async def run(self, request: AutoRequest) -> Dict[str, Any]:
        """
        Execute the given AutoRequest and return its response.

        Example
        -------
        ```python
        core = AutoCore()
        data = await core.run(WebBrowserRequest("https://example.org"))
        ```
        """
        return await request.execute()
