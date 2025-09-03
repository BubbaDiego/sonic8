import os, sys
from typing import Optional
from playwright.sync_api import sync_playwright

try:
    from auto_core.launcher.profile_utils import sanitize_profile_settings  # type: ignore
except Exception:
    THIS_DIR = os.path.dirname(__file__)
    PROJ_ROOT = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
    if PROJ_ROOT not in sys.path:
        sys.path.append(PROJ_ROOT)
    from auto_core.launcher.profile_utils import sanitize_profile_settings  # type: ignore

CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DEFAULT_URL = "https://jup.ag"
BASE_DIR   = r"C:\sonic5\profiles"

def _resolve_user_data_dir(wallet_id: str) -> str:
    if not wallet_id:
        raise SystemExit("[launcher] walletId is empty")
    if os.path.isabs(wallet_id):
        path = wallet_id
    else:
        path = os.path.join(BASE_DIR, wallet_id)
    os.makedirs(path, exist_ok=True)
    return path

def open_jupiter_with_wallet(wallet_id: str, url: Optional[str] = None, headless: bool = False) -> None:
    raw_user_data_dir = _resolve_user_data_dir(wallet_id)
    args = ["--no-first-run","--no-default-browser-check","--no-service-autorun"]
    user_data_dir, args = sanitize_profile_settings(raw_user_data_dir, args)
    with sync_playwright() as p:
        kw = dict(user_data_dir=user_data_dir, channel="chrome", headless=headless, args=args)
        if os.path.exists(CHROME_EXE): kw["executable_path"] = CHROME_EXE
        ctx = p.chromium.launch_persistent_context(**kw)
        page = ctx.new_page()
        page.goto(url or DEFAULT_URL, wait_until="domcontentloaded")
        page.bring_to_front()
        print(f"[OK] wallet='{wallet_id}' user_data_dir='{user_data_dir}' args={args}")
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
