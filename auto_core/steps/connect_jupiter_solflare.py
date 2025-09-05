"""Connect Solflare wallet on jup.ag via an existing Chrome instance."""

import json
import os
import re
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

JUP_URL = os.getenv("SONIC_JUPITER_URL", "https://jup.ag")
PORT = int(os.getenv("SONIC_CHROME_PORT", "0"))


def _pick_jup_page(ctx: BrowserContext, url: str) -> Page:
    """Return a page pointing at jup.ag, opening one if necessary."""
    for pg in ctx.pages:
        try:
            if "jup.ag" in (pg.url or ""):
                return pg
        except Exception:
            pass
    page = ctx.new_page()
    page.goto(url, wait_until="domcontentloaded")
    return page


def _already_connected(page: Page) -> bool:
    """Heuristic check if a wallet is already connected."""
    try:
        if page.get_by_role("button", name=re.compile("connect", re.I)).first.is_visible(timeout=500):
            return False
    except Exception:
        pass
    try:
        page.get_by_text(re.compile("Disconnect", re.I)).first
        return True
    except Exception:
        # If we can't find a Connect button, assume connected
        return True


def _find_extension_popup(browser: Browser, ctx: BrowserContext, solflare_id: str, wait_page: Page) -> Optional[Page]:
    """Listen for a new page matching the Solflare extension."""
    ext_page: Optional[Page] = None

    def _on_page(p: Page) -> None:
        nonlocal ext_page
        try:
            if p.url.startswith(f"chrome-extension://{solflare_id}"):
                ext_page = p
        except Exception:
            pass

    browser.on("page", _on_page)
    ctx.on("page", _on_page)

    for _ in range(32):  # ~8s
        if ext_page:
            break
        wait_page.wait_for_timeout(250)
    return ext_page


def _approve_popup(page: Page) -> None:
    """Attempt to click through approval buttons in the Solflare popup."""
    for label in ["Connect", "Approve", "Next", "Continue", "Confirm", "Allow"]:
        try:
            page.get_by_role("button", name=re.compile(label, re.I)).first.click(timeout=1200)
        except Exception:
            pass


def connect_jupiter_solflare() -> dict:
    """Attach to running Chrome via CDP and connect Solflare on jup.ag."""
    if not PORT:
        raise RuntimeError("SONIC_CHROME_PORT not set")

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = _pick_jup_page(ctx, JUP_URL)

        if _already_connected(page):
            return {"ok": True, "alreadyConnected": True}

        try:
            page.get_by_role("button", name=re.compile("connect", re.I)).first.click(timeout=3000)
        except Exception:
            page.locator("text=Connect").first.click(timeout=3000)

        try:
            page.get_by_role("button", name=re.compile("solflare", re.I)).first.click(timeout=3000)
        except Exception:
            page.locator("text=Solflare").first.click(timeout=3000)

        solflare_id = os.getenv("SOLFLARE_ID", "bhhhlbepdkbapadjdnnojkbgioiodbic")
        ext_page = _find_extension_popup(browser, ctx, solflare_id, page)
        if ext_page:
            _approve_popup(ext_page)
            page.bring_to_front()
            page.wait_for_timeout(1000)

        if not _already_connected(page):
            raise RuntimeError("Wallet still not connected")

        return {"ok": True, "connected": True}


if __name__ == "__main__":
    try:
        result = connect_jupiter_solflare()
        print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        raise
