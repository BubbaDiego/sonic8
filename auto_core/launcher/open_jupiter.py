from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright
from .chrome_profile_resolver import load_alias_map, resolve_profile_dir, ChromeProfileError

# --- CONFIG ---
CHROME_ALIAS_MAP = r"auto_core\config\chrome_profiles.json"
CHROME_EXE = r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
# Note: Use your existing Solflare CRX path if you want it loaded into the profile.
SOLFLARE_CRX = r"alpha\jupiter_core\solflare_extension.crx"  # from your memory items
JUPITER_URL = "https://jup.ag"  # or your deep link

def open_jupiter_with_profile(wallet_id: str, headless: bool = False, url: Optional[str] = None) -> None:
    alias_map = load_alias_map(CHROME_ALIAS_MAP)
    profile_path = resolve_profile_dir(wallet_id, alias_map)

    target_url = url or JUPITER_URL

    with sync_playwright() as p:
        # Use installed Chrome channel for proper profile handling + extension support
        browser = p.chromium.launch_persistent_context(
            user_data_dir=profile_path,
            channel="chrome",
            headless=headless,
            executable_path=CHROME_EXE,
            args=[
                # Keep the existing profile intact; do not isolate with a temp user-data-dir
                # Playwright will reuse the folder we passed as user_data_dir.
                f"--disable-extensions-except={SOLFLARE_CRX}",
                f"--load-extension={SOLFLARE_CRX}",
                "--no-first-run",
                "--disable-features=Translate"  # example: keep it stable
            ]
        )

        try:
            page = browser.new_page()
            page.goto(target_url, wait_until="domcontentloaded")
            # Optional: add your Jupiter connect automation here
            # e.g., page.click("text=Connect"), etc.
            page.bring_to_front()
            print(f"[OK] Opened {target_url} with profile: {profile_path}")
            # Keep the context open until user closes it via UI or code path
            page.wait_for_timeout(1500)  # small settle
        finally:
            # You probably keep it open for user interaction; omit close here
            pass

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--wallet-id", required=True, help="Alias from UI (e.g., Leia, R2, Lando)")
    ap.add_argument("--url", default=None)
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()
    try:
        open_jupiter_with_profile(args.wallet_id, headless=args.headless, url=args.url)
    except ChromeProfileError as e:
        print(f"[ERROR] {e}")
        raise SystemExit(2)
