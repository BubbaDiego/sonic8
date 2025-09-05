import os, sys
from typing import Optional
from playwright.sync_api import sync_playwright

# Package-safe import, with script-mode fallback
try:
    from auto_core.launcher.profile_utils import (
        sanitize_profile_settings,
        set_profile_display_name,
        mark_last_exit_clean,
    )
except Exception:
    THIS_DIR = os.path.dirname(__file__)
    PROJ_ROOT = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
    if PROJ_ROOT not in sys.path:
        sys.path.append(PROJ_ROOT)
    from auto_core.launcher.profile_utils import (
        sanitize_profile_settings,
        set_profile_display_name,
        mark_last_exit_clean,
    )

CHROME_EXE = r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
DEFAULT_URL = "https://jup.ag"
BASE_DIR   = r"C:\\sonic5\\profiles"   # all automation profiles live here
DEDICATED_ALIAS   = os.getenv("SONIC_AUTOPROFILE", "Sonic - Auto")
CONTROL_DIR       = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state")
CDP_PORT          = int(os.getenv("SONIC_CDP_PORT", "9224"))  # fixed port for attach

# --- helpers to suppress/dismiss the "Restore pages?" bubble ---
def _merge_disable_feature(args: list[str], feature: str) -> list[str]:
    """
    Ensure --disable-features includes the given feature.
    If Chrome sees two --disable-features flags, the *last* wins, so we prefer
    patching an existing flag; otherwise we append a new one.
    """
    for i, a in enumerate(args):
        if a.startswith("--disable-features="):
            payload = a.split("=", 1)[1]
            parts = [p.strip() for p in payload.split(",") if p.strip()]
            if feature not in parts:
                parts.append(feature)
                args[i] = f"--disable-features={','.join(parts)}"
            return args
    args.append(f"--disable-features={feature}")
    return args


def _install_restore_dismisser(ctx):
    """
    Attach a tiny watcher that closes the 'Restore pages?' bubble if it appears.
    Runs on the first page and any new pages in the context.
    """
    import re

    def _dismiss_on(page):
        # Try several selectors; click the Close/X, never the 'Restore' button.
        # We retry a few times in case the bubble animates in.
        candidates = [
            page.get_by_role("button", name=re.compile(r"^(Close|Dismiss)$", re.I)),
            page.locator('button[aria-label="Close"], button[aria-label="Dismiss"]'),
            # fallback: a button in a dialog that contains 'Restore pages?'
            page.locator('div:has-text("Restore pages")').locator('button[aria-label="Close"], button[aria-label="Dismiss"]'),
        ]
        for _ in range(10):
            for loc in candidates:
                try:
                    if loc.first.is_visible(timeout=200):
                        try:
                            loc.first.click(timeout=200)
                            return True
                        except Exception:
                            pass
                except Exception:
                    pass
            page.wait_for_timeout(250)
        return False

    # install on existing/new pages
    for p in ctx.pages:
        try:
            p.once("domcontentloaded", lambda _: _dismiss_on(p))
        except Exception:
            pass

    ctx.on("page", lambda p: p.once("domcontentloaded", lambda _: _dismiss_on(p)))

IGNORE_DEFAULT_ARGS = [
    "--disable-extensions",
    "--disable-component-extensions-with-background-pages",
]

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
    os.makedirs(CONTROL_DIR, exist_ok=True)
    control_flag = os.path.join(CONTROL_DIR, f"shutdown__{wallet_id.replace(os.sep,'_')}.flag")

    args = ["--no-first-run", "--no-default-browser-check", "--no-service-autorun"]
    args.append(f"--remote-debugging-port={CDP_PORT}")  # allow connect_over_cdp
    # Try to suppress the bubble at the source.
    args = _merge_disable_feature(args, "SessionCrashedBubble")
    if os.path.isdir(EXT_DIR):
        args += [f"--disable-extensions-except={EXT_DIR}", f"--load-extension={EXT_DIR}"]

    # Harden & set visible name
    user_data_dir, args = sanitize_profile_settings(raw_user_data_dir, args)
    # Pre-clear crash markers so we don't get 'Restore pages?'
    try:
        mark_last_exit_clean(user_data_dir, "Default")
    except Exception as e:
        print(f"[warn] mark_last_exit_clean failed: {e}")
    try:
        set_profile_display_name(user_data_dir, wallet_id)
    except Exception as e:
        print(f"[warn] set_profile_display_name failed: {e}")

    with sync_playwright() as p:
        kw = dict(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=headless,
            args=args,
            ignore_default_args=IGNORE_DEFAULT_ARGS,
        )
        if os.path.exists(CHROME_EXE):
            kw["executable_path"] = CHROME_EXE

        ctx = p.chromium.launch_persistent_context(**kw)

        # Publish CDP attach info for other routes
        try:
            os.makedirs(CONTROL_DIR, exist_ok=True)
            with open(os.path.join(CONTROL_DIR, "jupiter_cdp.json"), "w", encoding="utf-8") as f:
                import json
                json.dump({"alias": wallet_id, "port": CDP_PORT}, f)
        except Exception:
            pass

        # Install the auto-dismiss watcher for the restore bubble.
        _install_restore_dismisser(ctx)
        page = ctx.new_page()
        page.goto(url or DEFAULT_URL, wait_until="domcontentloaded")
        page.bring_to_front()
        print(f"[OK] wallet='{wallet_id}' user_data_dir='{user_data_dir}' args={args}")

        # Lightweight IPC loop — closes gracefully when the flag file appears
        import time
        try:
            while True:
                if os.path.exists(control_flag):
                    try:
                        os.remove(control_flag)
                    except Exception:
                        pass
                    break
                time.sleep(0.5)
        finally:
            # Graceful close to ensure Chrome records a clean exit
            try:
                ctx.close()
            except Exception:
                pass


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--wallet-id", required=True)
    ap.add_argument("--url", default=None)
    ap.add_argument("--headless", action="store_true")
    a = ap.parse_args()
    open_jupiter_with_wallet(a.wallet_id, a.url, a.headless)
