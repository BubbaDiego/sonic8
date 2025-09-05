import os, sys
from typing import Optional
from playwright.sync_api import sync_playwright

# pkg-safe import with script fallback
try:
    from auto_core.launcher.profile_utils import (
        sanitize_profile_settings,
        set_profile_display_name,
    )
except Exception:
    THIS_DIR = os.path.dirname(__file__)
    PROJ_ROOT = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
    if PROJ_ROOT not in sys.path:
        sys.path.append(PROJ_ROOT)
    from auto_core.launcher.profile_utils import (
        sanitize_profile_settings,
        set_profile_display_name,
    )

CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DEFAULT_URL = "https://jup.ag"
BASE_DIR    = r"C:\sonic5\profiles"
DEDICATED_ALIAS = os.getenv("SONIC_AUTOPROFILE", "Sonic - Auto")
DEBUG_PORT = int(os.getenv("SONIC_CHROME_PORT", "9230"))

# Allow store extensions by removing these Playwright defaults when possible
IGNORE_DEFAULT_ARGS = [
    "--disable-extensions",
    "--disable-component-extensions-with-background-pages",
]

# Optional: only if you intentionally want to load an unpacked extension
UNPACKED = os.getenv("SONIC_UNPACKED_SOLFLARE", "")  # e.g. C:\sonic5\extensions\solflare

def _resolve_user_data_dir(alias: str) -> str:
    alias = DEDICATED_ALIAS  # force canonical alias
    path = alias if os.path.isabs(alias) else os.path.join(BASE_DIR, alias)
    os.makedirs(path, exist_ok=True)
    return path

def _launch_with_fallback(p, kw: dict):
    """
    Try to launch with ignore_default_args to allow store extensions.
    If the Playwright build doesn't support it (UI-only crash), retry without it
    and force-enable extensions explicitly.
    """
    try:
        return p.chromium.launch_persistent_context(**kw)
    except TypeError:
        # Older Playwright that doesn't support ignore_default_args here
        kw.pop("ignore_default_args", None)
        kw["args"] = kw.get("args", []) + ["--enable-extensions"]
        return p.chromium.launch_persistent_context(**kw)
    except Exception as e:
        msg = str(e).lower()
        if "ignore_default_args" in msg or "disable-extensions" in msg:
            kw.pop("ignore_default_args", None)
            kw["args"] = kw.get("args", []) + ["--enable-extensions"]
            return p.chromium.launch_persistent_context(**kw)
        raise

def open_jupiter_with_wallet(wallet_id: str, url: Optional[str] = None, headless: bool = False) -> None:
    # Canonical alias only
    user_data_dir_raw = _resolve_user_data_dir(DEDICATED_ALIAS)

    args = [
        "--no-first-run",
        "--no-default-browser-check",
        "--no-service-autorun",
        f"--remote-debugging-port={DEBUG_PORT}",
    ]
    if UNPACKED and os.path.isdir(UNPACKED):
        args += [f"--disable-extensions-except={UNPACKED}", f"--load-extension={UNPACKED}"]

    # Sanitize any stray junk and set visible bubble name
    user_data_dir, args = sanitize_profile_settings(user_data_dir_raw, args)
    try:
        set_profile_display_name(user_data_dir, DEDICATED_ALIAS)
    except Exception as e:
        print(f"[warn] set_profile_display_name failed: {e}")

    with sync_playwright() as p:
        kw = dict(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=headless,
            args=args,
        )
        # Allow store extensions if supported by this Playwright build
        kw["ignore_default_args"] = IGNORE_DEFAULT_ARGS

        if os.path.exists(CHROME_EXE):
            kw["executable_path"] = CHROME_EXE

        ctx = _launch_with_fallback(p, kw)
        page = ctx.new_page()
        page.goto(url or DEFAULT_URL, wait_until="domcontentloaded")
        page.bring_to_front()
        print(
            f"[OK] user_data_dir='{user_data_dir}' port={DEBUG_PORT} args={args} ignore_default_args={IGNORE_DEFAULT_ARGS}"
        )
        while True:
            page.wait_for_timeout(60_000)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--wallet-id", required=True)   # ignored; we always use canonical alias
    ap.add_argument("--url", default=None)
    ap.add_argument("--headless", action="store_true")
    a = ap.parse_args()
    open_jupiter_with_wallet(a.wallet_id, a.url, a.headless)
