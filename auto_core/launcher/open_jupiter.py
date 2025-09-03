import os
from typing import Optional

from playwright.sync_api import sync_playwright


CHROME_EXE = r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
DEFAULT_URL = "https://jup.ag"
BASE_DIR = r"C:\\sonic5\\profiles"  # per-alias profiles live here


def _resolve_user_data_dir(wallet_id: str) -> str:
    if not wallet_id:
        raise SystemExit("[launcher] walletId is empty")
    # Allow absolute path pass-through (advanced usage)
    if os.path.isabs(wallet_id):
        path = wallet_id
    else:
        path = os.path.join(BASE_DIR, wallet_id)
    os.makedirs(path, exist_ok=True)
    return path


def open_jupiter_with_wallet(wallet_id: str, url: Optional[str] = None, headless: bool = False) -> None:
    user_data_dir = _resolve_user_data_dir(wallet_id)
    target_url = url or DEFAULT_URL

    with sync_playwright() as p:
        launch_kwargs = dict(
            user_data_dir=user_data_dir,  # THE ONLY profile selector
            channel="chrome",
            headless=headless,
            args=[
                "--no-first-run",
                "--no-default-browser-check",
                "--no-service-autorun",
            ],
        )
        if os.path.exists(CHROME_EXE):
            launch_kwargs["executable_path"] = CHROME_EXE

        # IMPORTANT: do NOT pass --profile-directory anywhere
        browser = p.chromium.launch_persistent_context(**launch_kwargs)
        try:
            page = browser.new_page()
            page.goto(target_url, wait_until="domcontentloaded")
            page.bring_to_front()
            print(f"[OK] {target_url} with wallet '{wallet_id}' @ {user_data_dir}")
            # keep alive until externally closed
            while True:
                page.wait_for_timeout(60_000)
        finally:
            pass


if __name__ == "__main__":
    import argparse
    import sys

    ap = argparse.ArgumentParser()
    ap.add_argument("--wallet-id", required=True)
    ap.add_argument("--url", default=None)
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()
    try:
        open_jupiter_with_wallet(args.wallet_id, url=args.url, headless=args.headless)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        raise SystemExit(2)

