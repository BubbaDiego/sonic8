"""
Lightweight wrapper around Playwright that boots a *persistent* Chromium
context with the Solflare extension preloaded.

For production use you will probably want to:
  • Parameterise the extension path.
  • Pull the Solflare seed phrase / password from HashiCorp Vault or AWS SM.
  • Handle multiple pages / queues and concurrency limits.
None of that is necessary for the v1 spike.
"""
from pathlib import Path
from typing import List
from playwright.async_api import async_playwright, Browser, Page
from backend.core.logging import log

SOLFLARE_CRX = Path("alpha/jupiter_core/solflare_extension.crx")
USER_DATA_DIR = Path(".cache/solflare_profile")  # persisted between runs


class PlaywrightHelper:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self._play = None
        self._browser: Browser | None = None

    async def __aenter__(self):
        try:
            self._play = await async_playwright().start()
            self._browser = await self._play.chromium.launch_persistent_context(
                USER_DATA_DIR,
                headless=self.headless,
                args=[
                    f"--disable-extensions-except={SOLFLARE_CRX}",
                    f"--load-extension={SOLFLARE_CRX}",
                ],
            )
            return self
        except Exception as e:  # pragma: no cover - startup issues depend on env
            msg = "Playwright failed to start – are browsers installed?"
            log.error(f"{msg}: {e}", source="PlaywrightHelper")
            raise

    async def __aexit__(self, exc_type, exc, tb):
        if self._browser:
            await self._browser.close()
        if self._play:
            await self._play.stop()

    async def open(self, url: str) -> Page:
        page = await self._browser.new_page()
        await page.goto(url)
        return page

    async def run_steps(self, page: Page, steps: List[str]) -> None:
        for step in steps:
            if step.startswith("click:"):
                selector = step.split("click:", 1)[1]
                await page.click(selector)
            elif step.startswith("wait:"):
                millis = int(step.split("wait:", 1)[1])
                await page.wait_for_timeout(millis)
