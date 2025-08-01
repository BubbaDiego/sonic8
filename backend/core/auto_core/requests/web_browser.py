import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from playwright.sync_api import sync_playwright
from .base import AutoRequest

_EXECUTOR = ThreadPoolExecutor(max_workers=1)
_USER_DATA_DIR = Path(".cache/solflare_profile")
_SOLFLARE_CRX = Path("alpha/jupiter_core/solflare_extension.crx")


def open_chrome_sync(url):
    with sync_playwright() as p:
        args = [
            f"--disable-extensions-except={_SOLFLARE_CRX}",
            f"--load-extension={_SOLFLARE_CRX}",
        ] if _SOLFLARE_CRX.exists() else []

        browser = p.chromium.launch_persistent_context(
            user_data_dir=_USER_DATA_DIR,
            headless=False,
            args=args
        )
        page = browser.new_page()
        page.goto(url)
        return {"url": page.url, "title": page.title()}


class WebBrowserRequest(AutoRequest):
    def __init__(self, url: str):
        self.url = url

    async def execute(self):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_EXECUTOR, open_chrome_sync, self.url)
