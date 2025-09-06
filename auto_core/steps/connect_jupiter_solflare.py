import os, re, sys
from typing import Optional
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
import time

PORT = int(os.getenv("SONIC_CHROME_PORT", "9230"))
TARGET = os.getenv("SONIC_JUPITER_URL", "https://jup.ag/perps")
# Use hardcoded password for Solflare unlock (can still be overridden by env)
PASS   = (os.getenv("SOLFLARE_PASS") or "1492braxx").strip()


def _pick_jup_page(browser):
    # Prefer an existing page on jup.ag
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if "jup.ag" in (pg.url or ""):
                return pg
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    pg = ctx.new_page()
    pg.goto(TARGET, wait_until="domcontentloaded")
    return pg


def _button_not_visible(page) -> bool:
    # Returns True if Connect button is not visible (assume already connected)
    try:
        page.get_by_role("button", name=re.compile(r"connect", re.I)).first.wait_for(state="visible", timeout=1200)
        return False
    except PWTimeout:
        return True
    except Exception:
        return True


def _find_extension_page(browser, timeout_ms: int = 7000):
    """
    Look across all contexts for a Solflare extension page (chrome-extension://...).
    Polls rather than using browser.wait_for_event('page') which doesn't exist.
    """
    deadline = time.time() + (timeout_ms / 1000.0)
    # quick pass: do we already have one?
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if (pg.url or "").startswith("chrome-extension://"):
                return pg
    # otherwise poll briefly
    while time.time() < deadline:
        for ctx in browser.contexts:
            # rescan existing pages
            for pg in ctx.pages:
                if (pg.url or "").startswith("chrome-extension://"):
                    return pg
            # also try to catch brand-new pages via context event
            try:
                new_pg = ctx.wait_for_event("page", timeout=250)
                if (new_pg.url or "").startswith("chrome-extension://"):
                    return new_pg
            except Exception:
                pass
        time.sleep(0.1)
    return None

def _connect_modal(page):
    """Return the Connect modal locator (role=dialog)."""
    try:
        modal = page.get_by_role("dialog", name=re.compile(r"connect", re.I))
        modal.wait_for(state="visible", timeout=3000)
        return modal
    except Exception:
        # Fallback: any visible dialog
        modal = page.locator('[role="dialog"]')
        try:
            modal.first.wait_for(state="visible", timeout=2000)
            return modal.first
        except Exception:
            return None

def _click_solflare_recently_used(page) -> bool:
    """
    Inside the Connect modal, click the **Recently Used** Solflare tile.
    We size-filter to avoid the tiny Quick Account icons.
    """
    modal = _connect_modal(page)
    if not modal:
        print("[connect] modal not visible")
        return False

    # Locate the "Recently Used" container (label then closest ancestor/section)
    try:
        ru_label = modal.get_by_text(re.compile(r"Recently Used", re.I)).first
        # nearest block-level ancestor of the label and following region
        ru = ru_label.locator('xpath=ancestor::div[1]/following::div[1]')
    except Exception:
        ru = modal  # fallback: whole modal

    # Collect clickable candidates that mention Solflare
    # (role buttons first, then generic clickable elements with text/aria-label)
    cands = []
    for loc in [
        ru.get_by_role("button", name=re.compile(r"solflare", re.I)),
        ru.locator('[role="button"][aria-label*="Solflare" i]'),
        ru.locator('button,[role=button],a').filter(has_text=re.compile(r"solflare", re.I)),
    ]:
        try:
            n = loc.count()
        except Exception:
            n = 0
        for i in range(n):
            el = loc.nth(i)
            try:
                box = el.bounding_box()
                if not box:
                    continue
                # prefer larger, tile-like buttons (avoid 24–32px icons)
                area = box["width"] * box["height"]
                if box["width"] >= 48 and box["height"] >= 48 and area >= 2400:
                    cands.append((area, el))
            except Exception:
                pass

    if not cands:
        print("[connect] RU Solflare tile not found (will try fallback list)")
        return False

    # Click the largest candidate (most likely the tile)
    cands.sort(key=lambda t: t[0], reverse=True)
    try:
        cands[0][1].click(timeout=1500)
        print("[connect] clicked RU Solflare tile")
        return True
    except Exception as e:
        print(f"[connect] RU tile click failed: {e}")
        return False

def _fallback_click_solflare_from_list(page) -> bool:
    """
    If RU tile isn’t present, open 'View More Wallets' and click Solflare (Extension).
    """
    modal = _connect_modal(page)
    if not modal:
        return False
    # Open the wallet list
    try:
        modal.get_by_text(re.compile(r"View More Wallets", re.I)).first.click(timeout=1500)
        time.sleep(0.2)
    except Exception:
        pass
    # Sometimes there’s a “Standard wallets” / “I already have a wallet” toggle
    for lab in [r"Standard", r"I already have a wallet", r"Wallets"]:
        try:
            modal.get_by_text(re.compile(lab, re.I)).first.click(timeout=800)
            time.sleep(0.1)
        except Exception:
            pass
    # Click Solflare (Extension) if present; otherwise any Solflare entry
    for pat in [r"Solflare.*Extension", r"Solflare"]:
        try:
            modal.get_by_role("button", name=re.compile(pat, re.I)).first.click(timeout=1500)
            print(f"[connect] clicked list item: {pat}")
            return True
        except Exception:
            pass
    print("[connect] fallback list did not contain Solflare")
    return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
        page = _pick_jup_page(browser)

        # S1: already connected?
        if _button_not_visible(page):
            print("[connect] already connected")
            return 0
        # If a stale Connect modal is open, dismiss and reopen (X button)
        try:
            stale = _connect_modal(page)
            if stale:
                stale.get_by_role("button", name=re.compile(r"close|×|x", re.I)).first.click(timeout=500)
                time.sleep(0.2)
        except Exception:
            pass

        # S2: open Connect modal
        page.get_by_role("button", name=re.compile(r"connect", re.I)).first.click(timeout=3000)
        # Wait for the modal to be visible
        _connect_modal(page)

        # S3: click Solflare tile **in Recently Used**; fallback to wallet list
        clicked = _click_solflare_recently_used(page)
        if not clicked:
            clicked = _fallback_click_solflare_from_list(page)

        if not clicked:
            print("[connect] could not find Solflare tile in modal")
            return 2

        # S4: unlock if prompted
        pop = _find_extension_page(browser)
        if pop:
            pop.bring_to_front()
            try:
                pop.locator('[data-testid="form-unlock"]').wait_for(state="visible", timeout=2500)
                try:
                    pwd = pop.locator('[data-testid="input-password"]').first
                    try:
                        pwd.click(timeout=800)
                    except Exception:
                        pass
                    pwd.fill(PASS, timeout=1500)
                    pop.locator('[data-testid="btn-unlock"]').first.click(timeout=1500)
                    time.sleep(0.5)
                except Exception:
                    pass
            except PWTimeout:
                # If no unlock form appears and Connect button missing, assume already connected
                if _button_not_visible(page):
                    print("[connect] already connected")
                    return 0

            # Some variants show approve/allow after unlock
            for label in [r"connect", r"approve", r"allow", r"continue", r"ok"]:
                try:
                    pop.get_by_role("button", name=re.compile(label, re.I)).first.click(timeout=800)
                    time.sleep(0.2)
                except Exception:
                    pass

        # S5: verify connected
        time.sleep(0.8)
        if _button_not_visible(page):
            print("[connect] success")
            return 0

        print("[connect] failed to verify connection")
        return 4


if __name__ == "__main__":
    sys.exit(main())

