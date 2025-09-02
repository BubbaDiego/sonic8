"""
Web-browser requests for Auto Core (Playwright + persistent Chrome).

Detachable persistent context so the window stays open after the request returns.
Enforces Windows Proactor event loop (correct for Playwright).
Loads Solflare extension only when present.
"""

import sys
import asyncio
import atexit
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Optional

from playwright.sync_api import sync_playwright

from .base import AutoRequest  # abstract request interface

# -----------------------------------------------------------------------------
# Windows event loop: keep Proactor (required by Playwright subprocess handling)
# -----------------------------------------------------------------------------
def _ensure_proactor_policy() -> None:
    """Ensure Windows uses ProactorEventLoopPolicy; no-ops on other OSes."""
    if not sys.platform.startswith("win"):
        return
    WP = getattr(asyncio, "WindowsProactorEventLoopPolicy", None)
    if WP is None:
        return
    if not isinstance(asyncio.get_event_loop_policy(), WP):
        asyncio.set_event_loop_policy(WP())

# -----------------------------------------------------------------------------
# Globals: one thread and one Playwright session for the whole process
# -----------------------------------------------------------------------------
_EXECUTOR: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=1)

# Persist Solflare login/state across runs (override with SOLFLARE_PROFILE_DIR)
_USER_DATA_DIR: Path = Path(os.getenv("SOLFLARE_PROFILE_DIR", ".cache/solflare_profile")).resolve()

# Optional Solflare extension (loaded if present; override with SOLFLARE_CRX_PATH)
_SOLFLARE_CRX: Path = Path(os.getenv("SOLFLARE_CRX_PATH", "alpha/jupiter_core/solflare_extension.crx")).resolve()

# Live session handles that exist only inside the worker thread
_PLAYWRIGHT = None  # type: Any
_CONTEXT = None     # type: Any

def _chrome_args() -> list[str]:
    """Build Chrome args, loading the Solflare CRX if present."""
    if _SOLFLARE_CRX.exists():
        return [
            f"--disable-extensions-except={_SOLFLARE_CRX}",
            f"--load-extension={_SOLFLARE_CRX}",
        ]
    return []

def _ensure_session(channel: Optional[str] = None) -> None:
    """
    Start Playwright and a persistent context if not already running.
    All calls happen inside the single worker thread.
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
            kwargs["channel"] = channel  # e.g., "chrome" to use system Chrome

        _CONTEXT = _PLAYWRIGHT.chromium.launch_persistent_context(**kwargs)

def _session_status() -> Dict[str, Any]:
    """Return current session status (for debugging/telemetry)."""
    status = {
        "playwright_started": _PLAYWRIGHT is not None,
        "context_open": bool(_CONTEXT and not _CONTEXT.is_closed()),
        "profile_dir": str(_USER_DATA_DIR),
        "extension_loaded": bool(_chrome_args()),
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
        etype = type(e).__name__
        # Keep responses structured even on failure; do not raise.
        return {
            "error": "open_failed",
            "etype": etype,
            "detail": str(e),
            **_session_status(),
        }

# ---------------------------------------------------------------------------
# Jupiter: open and click "Connect" (optionally choose a wallet)
# ---------------------------------------------------------------------------
def _jupiter_connect(target_url: str, select_wallet: Optional[str], channel: Optional[str]) -> Dict[str, Any]:
    """
    Navigate to Jupiter and click the 'Connect' button.
    If select_wallet is provided (e.g., 'solflare'), try to click that option in the wallet modal.
    Returns a structured status payload.
    """
    try:
        _ensure_session(channel=channel)
        page = _CONTEXT.new_page()
        page.goto(target_url, wait_until="domcontentloaded")

        # Dismiss common banners quietly (best-effort)
        for label in [r"Accept", r"I (agree|understand)", r"Continue", r"OK"]:
            try:
                page.get_by_role("button", name=re.compile(label, re.I)).first.click(timeout=1200)
            except Exception:
                pass

        # Prefer a proper role'd button named 'Connect'
        connect = None
        try:
            connect = page.get_by_role("button", name=re.compile(r"^Connect$", re.I)).first
            connect.wait_for(state="visible", timeout=5000)
        except Exception:
            # Fallbacks (header may render differently; bottom CTA also exists)
            try:
                connect = page.locator("button:has-text('Connect')").first
                connect.wait_for(state="visible", timeout=4000)
            except Exception:
                try:
                    connect = page.locator("text=Connect").first
                    connect.wait_for(state="visible", timeout=3000)
                except Exception:
                    return {
                        "error": "connect_button_not_found",
                        "url": page.url,
                        "title": page.title(),
                        **_session_status(),
                    }

        connect.click()

        modal_open = False
        wallet_clicked = False

        # If a wallet modal appears and a wallet was requested, click it
        try:
            # A tiny wait so the modal can animate in
            page.wait_for_timeout(500)
            # Heuristic: if any wallet option is visible, assume modal is open
            if page.locator("text=/Wallet|Connect Wallet|Solflare/i").first.is_visible(timeout=1500):
                modal_open = True
        except Exception:
            pass

        if modal_open and select_wallet:
            labels = []
            if select_wallet.lower() == "solflare":
                labels = [r"^Solflare$", r"Solflare.*Extension", r"Solflare Wallet"]
            else:
                labels = [re.escape(select_wallet)]
            for lb in labels:
                try:
                    page.get_by_role("button", name=re.compile(lb, re.I)).first.click(timeout=2500)
                    wallet_clicked = True
                    break
                except Exception:
                    try:
                        page.locator(f"text=/{lb}/i").first.click(timeout=1200)
                        wallet_clicked = True
                        break
                    except Exception:
                        pass

        return {
            "status": "clicked_connect",
            "modal_open": modal_open,
            "wallet_clicked": wallet_clicked,
            "selected_wallet": (select_wallet if wallet_clicked else None),
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

# Ensure cleanup at interpreter exit (best-effort)
def _cleanup_at_exit():
    """
    Best-effort cleanup at interpreter exit.
    IMPORTANT: run close *in the worker thread* that owns Playwright.
    If the executor is already shut down, ignore errors (process is exiting).
    """
    try:
        fut = _EXECUTOR.submit(_close_session)
        # Keep this timeout short; we don't want to hang on interpreter shutdown.
        fut.result(timeout=2)
    except Exception:
        # Executor may be gone or session already closed; ignore on exit.
        pass

atexit.register(_cleanup_at_exit)

# -----------------------------------------------------------------------------
# Requests
# -----------------------------------------------------------------------------
class WebBrowserRequest(AutoRequest):
    """
    Opens *url* in a persistent Chrome/Chromium profile (DETACHED).
    The call returns immediately; the browser window remains open.
    Optional *channel* = "chrome" to use system Chrome instead of bundled Chromium.
    """

    def __init__(self, url: str, channel: Optional[str] = None):
        self.url = url
        self.channel = channel  # None (default) = use bundled Chromium

    async def execute(self) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_EXECUTOR, _open_detached, self.url, self.channel)

class CloseBrowserRequest(AutoRequest):
    """Closes the persistent browser/context (if running)."""

    async def execute(self) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_EXECUTOR, _close_session)

# Optional: quick status probe without opening/closing
class BrowserStatusRequest(AutoRequest):
    """Returns current browser/context status."""

    async def execute(self) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_EXECUTOR, _session_status)

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

# Notes
#
# Do not use with sync_playwright() in this design — that closes the browser when the block exits.
#
# All Playwright calls happen in one worker thread to avoid cross-thread access to the context.
#
# The persistent user profile keeps Solflare’s state (logged-in/unlocked) between runs.
