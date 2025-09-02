"""
Web-browser requests for Auto Core (Playwright + persistent Chrome).

- Detached persistent context so the window stays open after the request returns
- Enforces Windows Proactor event loop for Playwright
- Loads Solflare extension only when present
"""

import os
import sys
import re
import atexit
import asyncio
from typing import Any, Dict, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from playwright.sync_api import sync_playwright

from .base import AutoRequest

# -----------------------------------------------------------------------------
# Windows event loop policy (Playwright needs Proactor on Windows)
# -----------------------------------------------------------------------------
def _ensure_proactor_policy() -> None:
    if not sys.platform.startswith("win"):
        return
    WP = getattr(asyncio, "WindowsProactorEventLoopPolicy", None)
    if WP and not isinstance(asyncio.get_event_loop_policy(), WP):
        asyncio.set_event_loop_policy(WP())

# -----------------------------------------------------------------------------
# One worker thread for all Playwright calls (thread-affinity)
# -----------------------------------------------------------------------------
_EXECUTOR: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=1)

# Paths (allow env overrides for convenience)
_USER_DATA_DIR = Path(os.getenv("SOLFLARE_PROFILE_DIR", ".cache/solflare_profile")).resolve()
_SOLFLARE_CRX = Path(os.getenv("SOLFLARE_CRX_PATH", "alpha/jupiter_core/solflare_extension.crx")).resolve()

# Live session handles (valid only inside the worker thread)
_PLAYWRIGHT = None  # type: Any
_CONTEXT = None     # type: Any

def _chrome_args() -> list[str]:
    if _SOLFLARE_CRX.exists():
        return [
            f"--disable-extensions-except={_SOLFLARE_CRX}",
            f"--load-extension={_SOLFLARE_CRX}",
        ]
    return []

def _ensure_session(channel: Optional[str] = None) -> None:
    """
    Start Playwright and a persistent context if not already running.
    Must run inside the worker thread.
    """
    global _PLAYWRIGHT, _CONTEXT
    _ensure_proactor_policy()

    if _PLAYWRIGHT is None:
        _PLAYWRIGHT = sync_playwright().start()

    if _CONTEXT is None or _CONTEXT.is_closed():
        kwargs = dict(
            user_data_dir=_USER_DATA_DIR,
            headless=False,
            args=_chrome_args(),
        )
        if channel:
            kwargs["channel"] = channel  # e.g., "chrome" for system Chrome
        _CONTEXT = _PLAYWRIGHT.chromium.launch_persistent_context(**kwargs)

def _session_status() -> Dict[str, Any]:
    status = {
        "playwright_started": _PLAYWRIGHT is not None,
        "context_open": bool(_CONTEXT and not _CONTEXT.is_closed()),
        "profile_dir": str(_USER_DATA_DIR),
        "extension_loaded": _SOLFLARE_CRX.exists(),
        "pages_open": 0,
    }
    try:
        if _CONTEXT and not _CONTEXT.is_closed():
            status["pages_open"] = len(_CONTEXT.pages)
    except Exception:
        pass
    return status

def _open_detached(url: str, channel: Optional[str]) -> Dict[str, Any]:
    """Open URL in a new page and return immediately (window stays open)."""
    try:
        _ensure_session(channel=channel)
        page = _CONTEXT.new_page()
        page.goto(url, wait_until="domcontentloaded")
        return {
            "mode": "detached",
            "url": page.url,
            "title": page.title(),
            **_session_status(),
        }
    except Exception as e:
        return {
            "error": "open_failed",
            "etype": type(e).__name__,
            "detail": str(e),
            **_session_status(),
        }

def _close_session() -> Dict[str, Any]:
    """Close the persistent context and stop Playwright."""
    global _PLAYWRIGHT, _CONTEXT
    try:
        if _CONTEXT and not _CONTEXT.is_closed():
            _CONTEXT.close()
    finally:
        _CONTEXT = None
        if _PLAYWRIGHT is not None:
            try:
                _PLAYWRIGHT.stop()
            finally:
                _PLAYWRIGHT = None
    return {"closed": True, **_session_status()}

def _cleanup_at_exit():
    """Run cleanup in the worker thread to avoid cross-thread closes on exit."""
    try:
        fut = _EXECUTOR.submit(_close_session)
        fut.result(timeout=2)
    except Exception:
        pass

atexit.register(_cleanup_at_exit)

# -----------------------------------------------------------------------------
# Public requests
# -----------------------------------------------------------------------------
class WebBrowserRequest(AutoRequest):
    """Open *url* in persistent Chrome/Chromium (detached return)."""
    def __init__(self, url: str, channel: Optional[str] = None):
        self.url = url
        self.channel = channel

    async def execute(self) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_EXECUTOR, _open_detached, self.url, self.channel)

class CloseBrowserRequest(AutoRequest):
    """Close the persistent browser/context (if any)."""
    async def execute(self) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_EXECUTOR, _close_session)

class BrowserStatusRequest(AutoRequest):
    """Return current status of the persistent session."""
    async def execute(self) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_EXECUTOR, _session_status)

# -----------------------------------------------------------------------------
# Jupiter: open and click "Connect" (and optionally click a wallet)
# -----------------------------------------------------------------------------
def _jupiter_connect(url: str, wallet: Optional[str], channel: Optional[str]) -> Dict[str, Any]:
    """
    Navigate to Jupiter and click the 'Connect' button.
    If wallet is provided (e.g., 'solflare'), try to click that option in the modal.
    """
    try:
        _ensure_session(channel=channel)
        page = _CONTEXT.new_page()
        page.goto(url, wait_until="domcontentloaded")

        # Try multiple selectors for 'Connect' to survive minor UI changes
        connect = None
        for try_fn in (
            lambda: page.get_by_role("button", name=re.compile(r"^Connect$", re.I)).first,
            lambda: page.locator("button:has-text('Connect')").first,
            lambda: page.locator("text=Connect").first,
        ):
            try:
                candidate = try_fn()
                candidate.wait_for(state="visible", timeout=5000)
                connect = candidate
                break
            except Exception:
                pass

        if connect is None:
            return {
                "error": "connect_button_not_found",
                "url": page.url,
                "title": page.title(),
                **_session_status(),
            }

        connect.click()

        # Give modal time to animate
        page.wait_for_timeout(500)

        modal_open = False
        try:
            # Any of these hints indicate a wallet modal
            if page.locator("text=/Wallet|Connect Wallet|Solflare/i").first.is_visible(timeout=1500):
                modal_open = True
        except Exception:
            pass

        wallet_clicked = False
        selected = None
        if modal_open and wallet:
            labels = (
                [r"^Solflare$", r"Solflare.*Extension", r"Solflare Wallet"]
                if wallet.lower() == "solflare"
                else [re.escape(wallet)]
            )
            for lb in labels:
                try:
                    page.get_by_role("button", name=re.compile(lb, re.I)).first.click(timeout=2500)
                    wallet_clicked = True
                    selected = wallet
                    break
                except Exception:
                    try:
                        page.locator(f"text=/{lb}/i").first.click(timeout=1500)
                        wallet_clicked = True
                        selected = wallet
                        break
                    except Exception:
                        pass

        return {
            "status": "clicked_connect",
            "modal_open": modal_open,
            "wallet_clicked": wallet_clicked,
            "selected_wallet": selected,
            "url": page.url,
            "title": page.title(),
            **_session_status(),
        }
    except Exception as e:
        return {
            "error": "jupiter_connect_failed",
            "etype": type(e).__name__,
            "detail": str(e),
            **_session_status(),
        }

class JupiterConnectRequest(AutoRequest):
    """
    Opens Jupiter (default https://jup.ag/perps), clicks 'Connect',
    and optionally clicks a wallet option (default: 'solflare').
    """
    def __init__(self, url: str = "https://jup.ag/perps", wallet: Optional[str] = "solflare", channel: Optional[str] = None):
        self.url = url
        self.wallet = wallet
        self.channel = channel

    async def execute(self) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_EXECUTOR, _jupiter_connect, self.url, self.wallet, self.channel)

