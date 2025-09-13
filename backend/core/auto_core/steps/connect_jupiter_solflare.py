# auto_core/steps/connect_jupiter_solflare.py
# --- Hard-coded Solflare unlock password (edit as needed) ---
SOLFLARE_UNLOCK_PASSWORD = "1492braxx"

import os, re, sys, time, socket
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

PORT   = int(os.getenv("SONIC_CHROME_PORT", "9230"))
TARGET = os.getenv("SONIC_JUPITER_URL", "https://jup.ag/perps")

# --------------------------- tiny utils ---------------------------

def _wait_port(port=PORT, host="127.0.0.1", deadline_s: float = 12.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < deadline_s:
        try:
            with socket.create_connection((host, port), timeout=0.3):
                return True
        except OSError:
            time.sleep(0.2)
    return False

def _already_connected(page) -> bool:
    """True if the 'Connect' button is NOT visible."""
    try:
        page.get_by_role("button", name=re.compile(r"connect", re.I)).first.wait_for(state="visible", timeout=700)
        return False
    except Exception:
        return True

def _visible_dialog(page):
    dlg = page.locator('[role="dialog"]:visible')
    try:
        dlg.first.wait_for(state="visible", timeout=1500)
        return dlg.first
    except Exception:
        pass
    dlg2 = page.locator('[role="dialog"][data-state="open"]')
    try:
        dlg2.first.wait_for(state="visible", timeout=1500)
        return dlg2.first
    except Exception:
        return None

def _ensure_modal(page) -> bool:
    # Close any stale dialog
    try:
        stale = page.locator('[role="dialog"]').first
        stale.get_by_role("button", name=re.compile(r"(close|×|x)", re.I)).first.click(timeout=350)
        time.sleep(0.15)
    except Exception:
        pass
    # Open fresh
    for _ in range(4):
        try:
            page.get_by_role("button", name=re.compile(r"connect", re.I)).first.click(timeout=2500)
        except Exception:
            pass
        if _visible_dialog(page):
            return True
        time.sleep(0.25)
    return False

def _try_click(loc, timeout=1800) -> bool:
    try:
        loc.wait_for(state="visible", timeout=timeout)
        loc.click(timeout=timeout)
        return True
    except Exception:
        return False

# --------------------------- click Solflare ------------------------

def _click_literally_solflare(container) -> bool:
    tries = [
        container.get_by_role("button", name=re.compile(r"^solflare$", re.I)).first,
        container.get_by_role("button", name=re.compile(r"solflare",   re.I)).first,
        container.locator("[role='button'][aria-label*='Solflare' i]").first,
        container.locator("button:has-text('Solflare')").first,
        container.locator("[role='button']:has-text('Solflare')").first,
    ]
    for loc in tries:
        if _try_click(loc, 2000):
            print("[connect] clicked 'Solflare' (button)")
            return True
    return False

def _click_ru_next_button(container) -> bool:
    """Click the first button after 'Recently Used' (icon-only RU tile)."""
    try:
        ru = container.get_by_text(re.compile(r"Recently Used", re.I)).first
        ru.wait_for(state="visible", timeout=1200)
        btn = ru.locator("xpath=following::button[1]").first
        if _try_click(btn, 1500):
            print("[connect] clicked RU next button after 'Recently Used'")
            return True
    except Exception:
        pass
    return False

def _click_icon_center(container, page) -> bool:
    """Click the Solflare icon center (works even if wrapper isn't a button)."""
    try:
        icon = container.locator("img[alt*='Solflare' i]").first
        icon.wait_for(state="visible", timeout=1500)
        box = icon.bounding_box()
        if box and box["width"] >= 20 and box["height"] >= 20:
            page.mouse.click(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            print("[connect] clicked Solflare icon center (mouse coords)")
            return True
    except Exception:
        pass
    return False

def _click_icon_ancestor(container) -> bool:
    """Click the clickable ancestor that wraps the Solflare icon."""
    try:
        icon = container.locator("img[alt*='Solflare' i]").first
        icon.wait_for(state="visible", timeout=1400)
        clickable = icon.locator("xpath=ancestor-or-self::button | ancestor-or-self::*[@role='button']").first
        if _try_click(clickable, 1800):
            print("[connect] clicked Solflare via image ancestor")
            return True
    except Exception:
        pass
    return False

def _view_more_then_click(page) -> bool:
    dlg = _visible_dialog(page)
    if dlg:
        _try_click(dlg.get_by_text(re.compile(r"View More Wallets", re.I)).first, 2200)
        time.sleep(0.3)
    return (
        _click_literally_solflare(page)
        or _click_icon_center(page, page)
        or _click_icon_ancestor(page)
    )

# ------------------- popup: unlock / approve -----------------------

def _find_popup(browser, timeout_s=10.0):
    """Find any Solflare extension popup page (unlock/confirm)."""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        for ctx in browser.contexts:
            for pg in ctx.pages:
                url = pg.url or ""
                if url.startswith("chrome-extension://"):
                    return pg
        time.sleep(0.15)
    return None

def _force_focus_and_type(pop) -> bool:
    """Brute-force: put caret into the password field region and type the password."""
    pw = SOLFLARE_UNLOCK_PASSWORD
    if not pw:
        print("[connect] WARN: hard-coded password empty")
        return False

    # Strategy A: direct selectors (fast path)
    selectors = [
        '[data-testid="input-password"]',
        'input[type="password"]',
        'input[autocomplete="current-password"]',
        'input[placeholder*="password" i]',
        'input[name*="password" i]',
    ]
    for sel in selectors:
        try:
            inp = pop.locator(sel).first
            inp.wait_for(state="visible", timeout=1000)
            inp.click(timeout=800)
            inp.fill(pw, timeout=1200)
            print(f"[connect] filled password via {sel}")
            return True
        except Exception:
            continue

    # Strategy B: click near label text then type with keyboard
    try:
        label = pop.get_by_text(re.compile(r"(Enter your password|Unlock Your Wallet)", re.I)).first
        label.wait_for(state="visible", timeout=1200)
        box = label.bounding_box()
        if box:
            # click 60px below the label's center (where the input usually is)
            pop.mouse.click(box["x"] + box["width"]/2, box["y"] + box["height"]/2 + 60)
            time.sleep(0.1)
            pop.keyboard.type(pw, delay=10)
            print("[connect] typed password via keyboard after label click")
            return True
    except Exception:
        pass

    # Strategy C: click center of any likely input container and type
    try:
        cont = pop.locator("input, [role='textbox'], [contenteditable='true']").first
        cont.wait_for(state="visible", timeout=1000)
        cont.click(timeout=800)
        pop.keyboard.type(pw, delay=10)
        print("[connect] typed password into generic editable")
        return True
    except Exception:
        pass

    return False

def _click_unlockish(pop) -> bool:
    # Prefer explicit "Unlock"
    if _try_click(pop.get_by_role("button", name=re.compile(r"^unlock$", re.I)).first, 1200):
        print("[connect] clicked Unlock")
        return True
    # Other continuations
    for lab in [r"continue", r"connect", r"approve", r"ok", r"done"]:
        if _try_click(pop.get_by_role("button", name=re.compile(lab, re.I)).first, 1200):
            print(f"[connect] clicked {lab}")
            return True
    # Try Enter
    try:
        pop.keyboard.press("Enter")
        print("[connect] pressed Enter")
        return True
    except Exception:
        return False

def _unlock_and_approve(pop):
    """Handle Solflare popup (top doc and any frames)."""
    # 1) top doc
    filled = _force_focus_and_type(pop)
    clicked = _click_unlockish(pop)

    # 2) frames (just in case future builds use them)
    for fr in pop.frames:
        try:
            filled = filled or _force_focus_and_type(fr)
            clicked = clicked or _click_unlockish(fr)
        except Exception:
            pass

    # 3) post-unlock approvals (top + frames)
    for lab in [r"connect", r"approve", r"allow", r"continue", r"ok", r"done"]:
        _try_click(pop.get_by_role("button", name=re.compile(lab, re.I)).first, 900)
        for fr in pop.frames:
            _try_click(fr.get_by_role("button", name=re.compile(lab, re.I)).first, 800)

# ------------------------------ main --------------------------------

def main():
    if not _wait_port():
        print(f"[connect] Chrome port {PORT} is not open")
        return 11

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")

        # Find or open the Perps tab
        page = None
        for ctx in browser.contexts:
            for pg in ctx.pages:
                if "jup.ag" in (pg.url or ""):
                    page = pg; break
            if page: break
        if not page:
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.new_page()
        try:
            if "/perps" not in (page.url or ""):
                page.goto(TARGET, wait_until="domcontentloaded")
        except Exception:
            pass

        # Bail if already connected
        if _already_connected(page):
            print("[connect] already connected")
            return 0

        # Ensure / use the connect modal
        dlg = _visible_dialog(page)
        if not dlg and not _ensure_modal(page):
            print("[connect] connect modal did not appear")
            return 12
        dlg = _visible_dialog(page)
        if not dlg:
            print("[connect] no visible dialog after ensure")
            return 12

        # Click Solflare: button → RU icon → View-More
        if not (
            _click_literally_solflare(dlg)
            or _click_ru_next_button(dlg)
            or _click_icon_center(dlg, page)
            or _click_icon_ancestor(dlg)
            or _view_more_then_click(page)
        ):
            print("[connect] could not find Solflare tile in modal")
            return 2

        # Handle popup (unlock + approve), with retries to survive delayed rendering
        t_deadline = time.time() + 14.0
        while time.time() < t_deadline:
            pop = _find_popup(browser, 2.0)
            if pop:
                pop.bring_to_front()
                _unlock_and_approve(pop)
                time.sleep(0.6)
                if _already_connected(page):
                    print("[connect] success")
                    return 0
            else:
                time.sleep(0.25)

        if _already_connected(page):
            print("[connect] success")
            return 0

        print("[connect] failed to verify connection")
        return 4

if __name__ == "__main__":
    sys.exit(main())
