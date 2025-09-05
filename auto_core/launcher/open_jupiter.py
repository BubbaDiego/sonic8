import os, sys
from typing import Optional
from playwright.sync_api import sync_playwright

# Package-safe import, with script-mode fallback
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

CHROME_EXE = r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
DEFAULT_URL = "https://jup.ag"
BASE_DIR   = r"C:\\sonic5\\profiles"   # all automation profiles live here
DEDICATED_ALIAS = os.getenv("SONIC_AUTOPROFILE", "Sonic - Auto")

# OPTIONAL: load Solflare from an unpacked folder so web store isn't needed
EXT_DIR = r"C:\\sonic5\\extensions\\solflare"  # must contain manifest.json

def _resolve_user_data_dir(wallet_id: str) -> str:
    if not wallet_id:
        raise SystemExit("[launcher] walletId is empty")
    path = wallet_id if os.path.isabs(wallet_id) else os.path.join(BASE_DIR, wallet_id)
    os.makedirs(path, exist_ok=True)
    return path


def open_jupiter_with_wallet(wallet_id: str, url: Optional[str] = None, headless: bool = False) -> None:
    # Ignore incoming value; always use the canonical alias
    wallet_id = DEDICATED_ALIAS
    raw_user_data_dir = _resolve_user_data_dir(wallet_id)

    args = ["--no-first-run", "--no-default-browser-check", "--no-service-autorun"]
    if os.path.isdir(EXT_DIR):
        args += [f"--disable-extensions-except={EXT_DIR}", f"--load-extension={EXT_DIR}"]

    # Harden & set visible name
    user_data_dir, args = sanitize_profile_settings(raw_user_data_dir, args)
    try:
        set_profile_display_name(user_data_dir, wallet_id)
    except Exception as e:
        print(f"[warn] set_profile_display_name failed: {e}")

    with sync_playwright() as p:
        kw = dict(user_data_dir=user_data_dir, channel="chrome", headless=headless, args=args)
        if os.path.exists(CHROME_EXE):
            kw["executable_path"] = CHROME_EXE

        ctx = p.chromium.launch_persistent_context(**kw)
        page = ctx.new_page()
        page.goto(url or DEFAULT_URL, wait_until="domcontentloaded")
        page.bring_to_front()
        print(f"[OK] wallet='{wallet_id}' user_data_dir='{user_data_dir}' args={args}")
        # Keep alive; the Close endpoint will kill by PID.
        while True:
            page.wait_for_timeout(60_000)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--wallet-id", required=True)
    ap.add_argument("--url", default=None)
    ap.add_argument("--headless", action="store_true")
    a = ap.parse_args()
    open_jupiter_with_wallet(a.wallet_id, a.url, a.headless)
