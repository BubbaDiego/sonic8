"""
WebBrowserRequest powered by Playwright + Solflare.
"""
from typing import List, Dict, Any
from ..playwright_helper import PlaywrightHelper
from .base import AutoRequest


class WebBrowserRequest(AutoRequest):
    """
    Navigate to ``url`` inside a Chromium profile that already has the
    Solflare wallet extension loaded.

    Parameters
    ----------
    url : str
        Initial URL to load.
    steps : list[str], optional
        Simple imperative commands, e.g. ``["click:#login", "wait:2000"]``.
        This *very* naïve format is good enough for smoke tests. Replace it
        with a richer domain‑specific language once requirements grow.
    """

    def __init__(self, url: str, steps: List[str] | None = None):
        self.url = url
        self.steps = steps or []

    async def execute(self) -> Dict[str, Any]:
        async with PlaywrightHelper() as helper:
            page = await helper.open(self.url)
            await helper.run_steps(page, self.steps)
            return {
                "url": page.url,
                "title": await page.title(),
                "steps_ran": self.steps,
            }
