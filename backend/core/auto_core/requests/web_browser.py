"""
Web-browser requests for Auto Core (Playwright + persistent Chrome).

- Detached persistent context so the window stays open after the request returns
- Enforces Windows Proactor event loop for Playwright
- Loads Solflare extension only when present
"""

import os, json
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
_WALLET_REGISTRY = Path(".cache/wallet_registry.json").resolve()
_WALLETS_ROOT = Path(".cache/wallets").resolve()

# Live session handles (valid only inside the worker thread)
_PLAYWRIGHT = None  # type: Any
_CONTEXT = None     # type: Any
# Multi-wallet contexts (one per wallet_id)
_CONTEXTS: dict[str, Any] = {}

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
    # NOTE: kept for backward-compat "default" single-context flows


def _load_registry() -> dict:
    try:
        if _WALLET_REGISTRY.exists():
            return json.loads(_WALLET_REGISTRY.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_registry(reg: dict) -> None:
    _WALLET_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    _WALLET_REGISTRY.write_text(json.dumps(reg, indent=2), encoding="utf-8")


def _resolve_wallet_profile(wallet_id: str | None, overrides: dict | None = None) -> dict:
    """
    Decide which profile to use for this wallet.
    Returns dict with: profile_dir, channel (optional), chrome_profile_directory (optional)
    """
    overrides = overrides or {}
    if not wallet_id:
        # Back-compat default profile
        return {
            "profile_dir": str(_USER_DATA_DIR),
            "channel": overrides.get("channel"),
            "chrome_profile_directory": overrides.get("chrome_profile_directory"),
        }
    reg = _load_registry()
    cfg = reg.get(wallet_id, {}).copy()
    # Build a safe default if missing
    if not cfg.get("profile_dir"):
        (_WALLETS_ROOT / wallet_id).mkdir(parents=True, exist_ok=True)
        cfg["profile_dir"] = str((_WALLETS_ROOT / wallet_id).resolve())
    # Apply per-call overrides
    for k in ("channel", "chrome_profile_directory"):
        if overrides.get(k) is not None:
            cfg[k] = overrides[k]
    return cfg


def _get_wallet_context(wallet_id: str | None, cfg: dict) -> Any:
    """
    Get or create a persistent context for the given wallet_id.
    Contexts live in the single worker thread.
    """
    global _PLAYWRIGHT
    _ensure_proactor_policy()
    if _PLAYWRIGHT is None:
        _PLAYWRIGHT = sync_playwright().start()

    # Use a key even for None -> "default"
    key = wallet_id or "default"
    ctx = _CONTEXTS.get(key)
    if ctx and not ctx.is_closed():
        return ctx

    args = _chrome_args()
    # If caller wants a specific Chrome subprofile inside a user_data_dir:
    if cfg.get("chrome_profile_directory"):
        args = args + [f'--profile-directory={cfg["chrome_profile_directory"]}']

    kwargs = dict(
        user_data_dir=Path(cfg["profile_dir"]),
        headless=False,
        args=args,
    )
    if cfg.get("channel"):
        kwargs["channel"] = cfg["channel"]  # e.g., "chrome"

    ctx = _PLAYWRIGHT.chromium.launch_persistent_context(**kwargs)
    _CONTEXTS[key] = ctx
    return ctx

def _session_status() -> Dict[str, Any]:
    status = {
        "playwright_started": _PLAYWRIGHT is not None,
        "context_open": bool(_CONTEXT and not _CONTEXT.is_closed()),  # legacy
        "profile_dir": str(_USER_DATA_DIR),
        "extension_loaded": _SOLFLARE_CRX.exists(),
        "pages_open": 0,
        "wallet_contexts": {
            k: {
                "open": (v is not None and not v.is_closed()),
                "pages_open": (len(v.pages) if v and not v.is_closed() else 0),
            }
            for k, v in list(_CONTEXTS.items())
        },
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
        # Back-compat default (no wallet_id); keep existing behavior
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


# Wallet-aware open (uses a specific wallet_id/profile)
def _open_with_wallet(
    url: str,
    wallet_id: Optional[str],
    channel: Optional[str],
    chrome_profile_directory: Optional[str],
) -> Dict[str, Any]:
    try:
        cfg = _resolve_wallet_profile(
            wallet_id,
            {
                "channel": channel,
                "chrome_profile_directory": chrome_profile_directory,
            },
        )
        ctx = _get_wallet_context(wallet_id, cfg)
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded")
        return {
            "mode": "detached",
            "wallet_id": wallet_id or "default",
            "profile_dir": cfg["profile_dir"],
            "url": page.url,
            "title": page.title(),
            **_session_status(),
        }
    except Exception as e:
        return {
            "error": "open_with_wallet_failed",
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
    # Also close all wallet contexts
    closed_wallets = []
    for k, ctx in list(_CONTEXTS.items()):
        try:
            if ctx and not ctx.is_closed():
                ctx.close()
                closed_wallets.append(k)
        except Exception:
            pass
        finally:
            _CONTEXTS.pop(k, None)
    return {"closed": True, "closed_wallets": closed_wallets, **_session_status()}


def _close_wallet(wallet_id: Optional[str]) -> Dict[str, Any]:
    key = wallet_id or "default"
    ctx = _CONTEXTS.get(key)
    if not ctx or ctx.is_closed():
        return {
            "closed": False,
            "wallet_id": key,
            "reason": "not_open",
            **_session_status(),
        }
    try:
        ctx.close()
        _CONTEXTS.pop(key, None)
        return {"closed": True, "wallet_id": key, **_session_status()}
    except Exception as e:
        return {
            "error": "close_wallet_failed",
            "etype": type(e).__name__,
            "detail": str(e),
            "wallet_id": key,
            **_session_status(),
        }

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


# -------- Wallet-aware requests ---------------------------------------------
class RegisterWalletRequest(AutoRequest):
    """Persist a mapping for wallet_id → profile_dir/channel/chrome_profile_directory."""

    def __init__(
        self,
        wallet_id: str,
        profile_dir: Optional[str] = None,
        channel: Optional[str] = None,
        chrome_profile_directory: Optional[str] = None,
    ):
        self.wallet_id = wallet_id
        self.profile_dir = profile_dir
        self.channel = channel
        self.chrome_profile_directory = chrome_profile_directory

    async def execute(self) -> Dict[str, Any]:
        def _do():
            reg = _load_registry()
            cfg = reg.get(self.wallet_id, {})
            if self.profile_dir:
                cfg["profile_dir"] = str(Path(self.profile_dir).resolve())
            else:
                (_WALLETS_ROOT / self.wallet_id).mkdir(parents=True, exist_ok=True)
                cfg["profile_dir"] = str((_WALLETS_ROOT / self.wallet_id).resolve())
            if self.channel is not None:
                cfg["channel"] = self.channel
            if self.chrome_profile_directory is not None:
                cfg["chrome_profile_directory"] = self.chrome_profile_directory
            reg[self.wallet_id] = cfg
            _save_registry(reg)
            return {"registered": True, "wallet_id": self.wallet_id, "config": cfg}

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_EXECUTOR, _do)


class WebBrowserWithWalletRequest(AutoRequest):
    """Open URL using the persistent context bound to wallet_id."""

    def __init__(
        self,
        url: str,
        wallet_id: Optional[str],
        channel: Optional[str] = None,
        chrome_profile_directory: Optional[str] = None,
    ):
        self.url = url
        self.wallet_id = wallet_id
        self.channel = channel
        self.chrome_profile_directory = chrome_profile_directory

    async def execute(self) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _EXECUTOR,
            _open_with_wallet,
            self.url,
            self.wallet_id,
            self.channel,
            self.chrome_profile_directory,
        )

# -----------------------------------------------------------------------------
# Jupiter: open and click "Connect" (and optionally click a wallet)
# -----------------------------------------------------------------------------
def _jupiter_connect(
    url: str,
    wallet: Optional[str],
    channel: Optional[str],
    wallet_id: Optional[str] = None,
    chrome_profile_directory: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Navigate to Jupiter and click the 'Connect' button.
    If wallet is provided (e.g., 'solflare'), try to click that option in the modal.
    """
    try:
        cfg = _resolve_wallet_profile(
            wallet_id,
            {"channel": channel, "chrome_profile_directory": chrome_profile_directory},
        )
        ctx = _get_wallet_context(wallet_id, cfg)
        page = ctx.new_page()
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
            "wallet_id": wallet_id or "default",
            "profile_dir": cfg["profile_dir"],
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

    def __init__(
        self,
        url: str = "https://jup.ag/perps",
        wallet: Optional[str] = "solflare",
        channel: Optional[str] = None,
        wallet_id: Optional[str] = None,
        chrome_profile_directory: Optional[str] = None,
    ):
        self.url = url
        self.wallet = wallet
        self.channel = channel
        self.wallet_id = wallet_id
        self.chrome_profile_directory = chrome_profile_directory

    async def execute(self) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _EXECUTOR,
            _jupiter_connect,
            self.url,
            self.wallet,
            self.channel,
            self.wallet_id,
            self.chrome_profile_directory,
        )


class CloseWalletRequest(AutoRequest):
    """Close only the wallet-specific context."""

    def __init__(self, wallet_id: Optional[str]):
        self.wallet_id = wallet_id

    async def execute(self) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_EXECUTOR, _close_wallet, self.wallet_id)

