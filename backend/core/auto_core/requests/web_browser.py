"""Web‑browser request for Auto Core (Playwright + Chrome).

* Ensures the Windows SelectorEventLoopPolicy is active BOTH in the main
  thread and inside the worker thread that actually runs Playwright.
* Loads Solflare extension only when present.
"""

import sys
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from playwright.sync_api import sync_playwright

from .base import AutoRequest

# ---------------------------------------------------------------------------
# Event‑loop policy helper
# ---------------------------------------------------------------------------
def _ensure_selector_policy():
    """Switch to SelectorEventLoopPolicy on Windows if still using Proactor."""
    if (
        sys.platform.startswith("win")
        and isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy)
    ):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# Apply at import‑time for the main thread.
_ensure_selector_policy()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_EXECUTOR: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=1)

_USER_DATA_DIR: Path = Path(".cache/solflare_profile")
_SOLFLARE_CRX: Path = Path("alpha/jupiter_core/solflare_extension.crx").resolve()


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def _chrome_args() -> list[str]:
    if _SOLFLARE_CRX.exists():
        return [
            f"--disable-extensions-except={_SOLFLARE_CRX}",
            f"--load-extension={_SOLFLARE_CRX}",
        ]
    return []


def _open_chrome_sync(url: str):
    """Runs inside a thread; make *sure* the selector policy is active here too."""
    _ensure_selector_policy()

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=_USER_DATA_DIR,
            headless=False,
            args=_chrome_args(),
        )
        page = browser.new_page()
        page.goto(url)
        return {"url": page.url, "title": page.title()}


# ---------------------------------------------------------------------------
# Public Auto Core request
# ---------------------------------------------------------------------------
class WebBrowserRequest(AutoRequest):
    """Opens *url* in a persistent Chrome profile."""

    def __init__(self, url: str):
        self.url = url

    async def execute(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_EXECUTOR, _open_chrome_sync, self.url)