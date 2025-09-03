from pathlib import Path
from typing import Optional
import json
import sys
from datetime import datetime
from playwright.sync_api import sync_playwright
from .chrome_profile_resolver import load_alias_map, resolve_profile_dir, ChromeProfileError

ALIAS_MAP_PATH = Path("auto_core/config/chrome_profiles.json")
LAUNCHER_CFG_PATH = Path("auto_core/config/chrome_launcher_config.json")

def _load_launcher_cfg():
    if not LAUNCHER_CFG_PATH.exists():
        return {}
    with LAUNCHER_CFG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def open_jupiter_with_profile(wallet_id: str, headless: bool = False, url: Optional[str] = None) -> None:
    alias_map = load_alias_map(str(ALIAS_MAP_PATH))
    profile_path = resolve_profile_dir(wallet_id, alias_map)  # absolute dir

    cfg = _load_launcher_cfg()
    chrome_exe = cfg.get("chrome_exe")
    chrome_channel = cfg.get("chrome_channel", "chrome")
    solflare_crx = cfg.get("solflare_crx")
    load_solflare = cfg.get("load_solflare", False)
    extra_args = cfg.get("extra_args", [])

    args = list(extra_args)
    if load_solflare and solflare_crx:
        args += [f"--disable-extensions-except={solflare_crx}", f"--load-extension={solflare_crx}"]

    jupiter_url = url or "https://jup.ag"

    print(f"[{datetime.now().isoformat()}] Launching Chrome with user_data_dir={profile_path}")
    with sync_playwright() as p:
        launch_kwargs = dict(
            user_data_dir=profile_path,
            channel=chrome_channel,
            headless=headless,
            args=args
        )
        if chrome_exe and Path(chrome_exe).exists():
            launch_kwargs["executable_path"] = chrome_exe

        browser = p.chromium.launch_persistent_context(**launch_kwargs)
        try:
            page = browser.new_page()
            page.goto(jupiter_url, wait_until="domcontentloaded")
            page.bring_to_front()
            print(f"[OK] Opened {jupiter_url} with alias '{wallet_id}' @ {profile_path}")
            while True:
                page.wait_for_timeout(60_000)
        finally:
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
        print(f"[ERROR] {e}", file=sys.stderr)
        raise SystemExit(2)
