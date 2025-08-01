"""
WebBrowserRequest
-----------------
Opens a URL in a real Chromium instance via Playwright.  Uses Playwright’s
*synchronous* API under the hood, executed in a worker thread, so it works
fine on Windows without forcing the Selector‑event‑loop hack.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Any

from playwright.sync_api import sync_playwright

from .base import AutoRequest

_SOLFLARE_CRX = Path("alpha/jupiter_core/solflare_extension.crx")
_USER_DATA_DIR = Path(".cache/solflare_profile")
_EXECUTOR = ThreadPoolExecutor(max_workers=1)


def _sync_launch(url: str, headless: bool) -> Dict[str, Any]:
    with sync_playwright() as pw:
        args = []
        if _SOLFLARE_CRX.exists():
            args.extend([
                f"--disable-extensions-except={_SOLFLARE_CRX}",
                f"--load-extension={_SOLFLARE_CRX}",
            ])
        ctx = pw.chromium.launch_persistent_context(
            _USER_DATA_DIR,
            headless=headless,
            args=args,
        )
        page = ctx.new_page()
        page.goto(url)
        title = page.title()
        if headless:
            ctx.close()
        return {"url": page.url, "title": title}


class WebBrowserRequest(AutoRequest):
    def __init__(self, url: str, *, headless: bool = False):
        self.url = url
        self.headless = headless

    async def execute(self) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            _EXECUTOR, _sync_launch, self.url, self.headless
        )
