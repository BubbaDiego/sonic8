"""
Web-browser requests for Auto Core (Playwright + persistent Chrome).

- Detached persistent contexts so the window stays open after the request returns
- Enforces Windows Proactor event loop for Playwright
- Supports wallet-specific Chrome profiles (Option A/B)
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
# Multi-wallet contexts (one per wallet_id) + metadata
_CONTEXTS: dict[str, Any] = {}
_CONTEXT_META: dict[str, dict] = {}

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _norm(wid: str | None) -> str | None:
    if wid is None:
        return None
    return wid.strip().lower().replace(" ", "-")

def _context_is_closed(ctx: Any) -> bool:
    """Return True if a Playwright ``BrowserContext`` appears closed."""
    try:
        attr = getattr(ctx, "is_closed", None)
        if callable(attr):
            return bool(attr())
        if attr is not None:
            return bool(attr)
        return bool(getattr(ctx, "closed", False))
    except Exception:
        return True

def _find_chrome_exe() -> Optional[str]:
    """Locate system Chrome on Windows (user-level first, then Program Files)."""
    for p in (
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ):
        if os.path.exists(p):
            return p
    return None

def _chrome_args_for_channel(channel: Optional[str]) -> list[str]:
    """
    Safe flags for launch. For system Chrome we DO NOT inject extensions here
    (profiles manage their own). For bundled Chromium, only inject an unpacked
    extension directory (never a .crx file).
    """
    base = ["--no-first-run", "--no-default-browser-check", "--no-service-autorun"]
    if channel == "chrome":
        return base
    if _SOLFLARE_CRX.exists() and _SOLFLARE_CRX.is_dir():
        return base + [
            f"--disable-extensions-except={_SOLFLARE_CRX}",
            f"--load-extension={_SOLFLARE_CRX}",
        ]
    return base

# -----------------------------------------------------------------------------
# Registry I/O
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# Default (legacy) single-context path
# -----------------------------------------------------------------------------
def _ensure_session(channel: Optional[str] = None) -> None:
    """
    Start Playwright and a persistent context if not already running.
    Must run inside the worker thread.
    """
    global _PLAYWRIGHT, _CONTEXT
    _ensure_proactor_policy()

    if _PLAYWRIGHT is None:
        _PLAYWRIGHT = sync_playwright().start()

    if _CONTEXT is None or _context_is_closed(_CONTEXT):
        args = _chrome_args_for_channel(channel)
        kwargs: Dict[str, Any] = dict(
            user_data_dir=_USER_DATA_DIR,
            headless=False,
            args=args,
        )
        if channel == "chrome":
            exe = _find_chrome_exe()
            if exe:
                kwargs["executable_path"] = exe
            else:
                kwargs["channel"] = "chrome"
        elif channel:
            kwargs["channel"] = channel

        _CONTEXT = _PLAYWRIGHT.chromium.launch_persistent_context(**kwargs)
    # NOTE: kept for backward-compat "default" single-context flows

# -----------------------------------------------------------------------------
# Wallet context management
# -----------------------------------------------------------------------------
def _resolve_wallet_profile(wallet_id: str | None, overrides: dict | None = None) -> dict:
    """
    Decide which profile to use for this wallet.
    Returns dict with keys: profile_dir, channel (optional), chrome_profile_directory (optional)
    """
    overrides = overrides or {}
    wallet_id = _norm(wallet_id)
    if not wallet_id:
        return {
            "profile_dir": str(_USER_DATA_DIR),
            "channel": overrides.get("channel"),
            "chrome_profile_directory": overrides.get("chrome_profile_directory"),
        }
    reg = _load_registry()
    cfg = reg.get(wallet_id, {}).copy()
    if not cfg.get("profile_dir"):
        (_WALLETS_ROOT / wallet_id).mkdir(parents=True, exist_ok=True)
        cfg["profile_dir"] = str((_WALLETS_ROOT / wallet_id).resolve())
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

    key = (_norm(wallet_id) or "default")
    ctx = _CONTEXTS.get(key)
    if ctx and not _context_is_closed(ctx):
        return ctx

    # Preflight paths
    pdir = Path(cfg["profile_dir"])
    if not pdir.exists():
        raise RuntimeError(f"profile_dir does not exist: {pdir}")
    sub = cfg.get("chrome_profile_directory")
    if sub and not (pdir / sub).exists():
        raise RuntimeError(f"chrome_profile_directory not found under profile_dir: {(pdir / sub)}")

    # Build args/kwargs
    args = _chrome_args_for_channel(cfg.get("channel"))
    if sub:
        args.append(f'--profile-directory={sub}')

    kwargs: Dict[str, Any] = dict(
        user_data_dir=pdir,
        headless=False,
        args=args,
        ignore_default_args=[
            "--disable-extensions",
            "--disable-component-extensions-with-background-pages",
            "--password-store=basic",
            "--use-mock-keychain",
        ],
    )

    exe = None
    if cfg.get("channel") == "chrome":
        exe = _find_chrome_exe()
        if exe:
            kwargs["executable_path"] = exe
        else:
            kwargs["channel"] = "chrome"
    elif cfg.get("channel"):
        kwargs["channel"] = cfg["channel"]

    try:
        ctx = _PLAYWRIGHT.chromium.launch_persistent_context(**kwargs)
    except Exception as e:
        raise RuntimeError(
            f"failed to launch Chrome with user_data_dir={pdir}, profile={sub}, "
            f"exe={exe}, channel={cfg.get('channel')}, args={args}: {e}"
        ) from e

    _CONTEXTS[key] = ctx
    _CONTEXT_META[key] = {
        "profile_dir": str(pdir.resolve()),
        "channel": cfg.get("channel"),
        "chrome_profile_directory": sub,
        "args": args,
        "executable_path": exe,
    }
    return ctx

def _session_status() -> Dict[str, Any]:
    status = {
        "playwright_started": _PLAYWRIGHT is not None,
        "context_open": bool(_CONTEXT and not _context_is_closed(_CONTEXT)),  # legacy default
        "profile_dir": str(_USER_DATA_DIR),
        "extension_loaded": _SOLFLARE_CRX.exists(),
        "pages_open": 0,
        "wallet_contexts": {}
    }
    try:
        if _CONTEXT and not _context_is_closed(_CONTEXT):
            status["pages_open"] = len(_CONTEXT.pages)
    except Exception:
        pass
    for k, v in list(_CONTEXTS.items()):
        open_ = (v is not None and not _context_is_closed(v))
        meta = _CONTEXT_META.get(k, {})
        status["wallet_contexts"][k] = {
            "open": open_,
            "pages_open": (len(v.pages) if open_ else 0),
            "profile_dir": meta.get("profile_dir"),
            "channel": meta.get("channel"),
            "chrome_profile_directory": meta.get("chrome_profile_directory"),
            "executable_path": meta.get("executable_path"),
        }
    return status

# -----------------------------------------------------------------------------
# Default open (legacy)
# -----------------------------------------------------------------------------
def _open_detached(url: str, channel: Optional[str]) -> Dict[str, Any]:
    """Open URL in a new page and return immediately (window stays open)."""
    try:
        _ensure_session(channel=channel)
        page = _CONTEXT.new_page()
        page.goto(url, wait_until="domcontentloaded")
        ua = ""
        try:
            ua = page.evaluate("navigator.userAgent")
        except Exception:
            pass
        info = _session_status()
        info.update({
            "mode": "detached",
            "url": page.url,
            "title": page.title(),
            "engine_user_agent": ua,
        })
        return info
    except Exception as e:
        return {"error": "open_failed", "etype": type(e).__name__, "detail": str(e), **_session_status()}

# -----------------------------------------------------------------------------
# Wallet-aware open
# -----------------------------------------------------------------------------
def _open_with_wallet(
    url: str,
    wallet_id: Optional[str],
    channel: Optional[str],
    chrome_profile_directory: Optional[str],
) -> Dict[str, Any]:
    try:
        cfg = _resolve_wallet_profile(
            wallet_id,
            {"channel": channel, "chrome_profile_directory": chrome_profile_directory},
        )
        ctx = _get_wallet_context(wallet_id, cfg)
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded")
        ua = ""
        try:
            ua = page.evaluate("navigator.userAgent")
        except Exception:
            pass
        meta = _CONTEXT_META.get(_norm(wallet_id) or "default", {})
        info = _session_status()
        info.update({
            "mode": "detached",
            "wallet_id": wallet_id or "default",
            "profile_dir": cfg["profile_dir"],
            "channel": cfg.get("channel"),
            "chrome_profile_directory": cfg.get("chrome_profile_directory"),
            "launch_args": meta.get("args"),
            "executable_path": meta.get("executable_path"),
            "engine_user_agent": ua,
            "url": page.url,
            "title": page.title(),
        })
        return info
    except Exception as e:
        return {"error": "open_with_wallet_failed", "etype": type(e).__name__, "detail": str(e), **_session_status()}

# -----------------------------------------------------------------------------
# Close contexts
# -----------------------------------------------------------------------------
def _close_session() -> Dict[str, Any]:
    """Close the persistent context and stop Playwright."""
    global _PLAYWRIGHT, _CONTEXT
    try:
        if _CONTEXT and not _context_is_closed(_CONTEXT):
            _CONTEXT.close()
    finally:
        _CONTEXT = None
        if _PLAYWRIGHT is not None:
            try:
                _PLAYWRIGHT.stop()
            finally:
                _PLAYWRIGHT = None
    closed_wallets = []
    for k, ctx in list(_CONTEXTS.items()):
        try:
            if ctx and not _context_is_closed(ctx):
                ctx.close()
                closed_wallets.append(k)
        except Exception:
            pass
        finally:
            _CONTEXTS.pop(k, None)
            _CONTEXT_META.pop(k, None)
    return {"closed": True, "closed_wallets": closed_wallets, **_session_status()}

def _close_wallet(wallet_id: Optional[str]) -> Dict[str, Any]:
    key = (_norm(wallet_id) or "default")
    ctx = _CONTEXTS.get(key)
    if not ctx or _context_is_closed(ctx):
        return {"closed": False, "wallet_id": key, "reason": "not_open", **_session_status()}
    try:
        ctx.close()
        _CONTEXTS.pop(key, None)
        _CONTEXT_META.pop(key, None)
        return {"closed": True, "wallet_id": key, **_session_status()}
    except Exception as e:
        return {"error": "close_wallet_failed", "etype": type(e).__name__, "detail": str(e), "wallet_id": key, **_session_status()}

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

# ---- List registered wallets ------------------------------------------------
class ListWalletsRequest(AutoRequest):
    """Return registry contents and which wallet contexts are currently open."""
    async def execute(self):
        def _do():
            reg = _load_registry()  # reads .cache/wallet_registry.json
            return {"wallets": reg, **_session_status()}
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_EXECUTOR, _do)

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
            wid = _norm(self.wallet_id)
            cfg = reg.get(wid, {})
            if self.profile_dir:
                cfg["profile_dir"] = str(Path(self.profile_dir).resolve())
            else:
                (_WALLETS_ROOT / wid).mkdir(parents=True, exist_ok=True)
                cfg["profile_dir"] = str((_WALLETS_ROOT / wid).resolve())
            if self.channel is not None:
                cfg["channel"] = self.channel
            if self.chrome_profile_directory is not None:
                cfg["chrome_profile_directory"] = self.chrome_profile_directory
            reg[wid] = cfg
            _save_registry(reg)
            return {"registered": True, "wallet_id": wid, "config": cfg}
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
            return {"error": "connect_button_not_found", "url": page.url, "title": page.title(), **_session_status()}

        connect.click()
        page.wait_for_timeout(500)  # modal animation

        modal_open = False
        try:
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

        ua = ""
        try:
            ua = page.evaluate("navigator.userAgent")
        except Exception:
            pass
        meta = _CONTEXT_META.get(_norm(wallet_id) or "default", {})
        info = _session_status()
        info.update({
            "status": "clicked_connect",
            "modal_open": modal_open,
            "wallet_clicked": wallet_clicked,
            "selected_wallet": selected,
            "wallet_id": wallet_id or "default",
            "profile_dir": cfg["profile_dir"],
            "channel": cfg.get("channel"),
            "chrome_profile_directory": cfg.get("chrome_profile_directory"),
            "engine_user_agent": ua,
            "launch_args": meta.get("args"),
            "executable_path": meta.get("executable_path"),
            "url": page.url,
            "title": page.title(),
        })
        return info
    except Exception as e:
        return {"error": "jupiter_connect_failed", "etype": type(e).__name__, "detail": str(e), **_session_status()}

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
