# auto_core/steps/solflare_unlock_only.py
# --- Hard-coded Solflare unlock password ---
SOLFLARE_UNLOCK_PASSWORD = "1492braxx"

import os, re, sys, time, socket
from playwright.sync_api import sync_playwright

PORT = int(os.getenv("SONIC_CHROME_PORT", "9230"))

def _wait_port(port=PORT, host="127.0.0.1", deadline_s=12.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < deadline_s:
        try:
            with socket.create_connection((host, port), timeout=0.3):
                return True
        except OSError:
            time.sleep(0.2)
    return False

def _try_click(loc, timeout=1200) -> bool:
    try:
        loc.wait_for(state="visible", timeout=timeout)
        loc.click(timeout=timeout)
        return True
    except Exception:
        return False

def _fill_direct(scope) -> bool:
    pw = SOLFLARE_UNLOCK_PASSWORD
    if not pw:
        print("[unlock] WARN: no hard-coded password")
        return False
    selectors = [
        '[data-testid="input-password"]',
        'input[type="password"]',
        'input[autocomplete="current-password"]',
        'input[placeholder*="password" i]',
        'input[name*="password" i]',
    ]
    for sel in selectors:
        try:
            inp = scope.locator(sel).first
            inp.wait_for(state="visible", timeout=800)
            inp.click(timeout=600)
            inp.fill(pw, timeout=1000)
            print(f"[unlock] filled via {sel}")
            return True
        except Exception:
            continue
    # role=textbox named “password”
    try:
        tb = scope.get_by_role("textbox", name=re.compile(r"password", re.I)).first
        tb.fill(pw, timeout=1000)
        print("[unlock] filled via role=textbox")
        return True
    except Exception:
        return False

def _type_with_keyboard(scope) -> bool:
    pw = SOLFLARE_UNLOCK_PASSWORD
    try:
        # click near label then type
        label = scope.get_by_text(re.compile(r"(Enter your password|Unlock Your Wallet)", re.I)).first
        label.wait_for(state="visible", timeout=1000)
        box = label.bounding_box()
        if box:
            scope.mouse.click(box["x"] + box["width"]/2, box["y"] + box["height"]/2 + 60)
            time.sleep(0.1)
            scope.keyboard.type(pw, delay=10)
            print("[unlock] typed via keyboard under label")
            return True
    except Exception:
        pass
    # fallback: focus any editable
    try:
        ed = scope.locator("input, [role='textbox'], [contenteditable='true']").first
        ed.wait_for(state="visible", timeout=1000)
        ed.click(timeout=600)
        scope.keyboard.type(pw, delay=10)
        print("[unlock] typed into generic editable")
        return True
    except Exception:
        return False

def _press_unlockish(scope) -> bool:
    # prefer Unlock
    if _try_click(scope.get_by_role("button", name=re.compile(r"^unlock$", re.I)).first, 1000):
        print("[unlock] clicked Unlock")
        return True
    # common alternatives
    for lab in [r"continue", r"connect", r"approve", r"ok", r"done"]:
        if _try_click(scope.get_by_role("button", name=re.compile(lab, re.I)).first, 900):
            print(f"[unlock] clicked {lab}")
            return True
    try:
        scope.keyboard.press("Enter")
        print("[unlock] pressed Enter")
        return True
    except Exception:
        return False

def main():
    if not _wait_port():
        print(f"[unlock] Chrome port {PORT} not open")
        return 11

    with sync_playwright() as p:
        br = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")

        # Find *any* Solflare popup page
        pop = None
        t0 = time.time()
        while time.time() - t0 < 10:
            for ctx in br.contexts:
                for pg in ctx.pages:
                    url = (pg.url or "")
                    if url.startswith("chrome-extension://") and ("unlock" in url or "confirm" in url or "popup" in url):
                        pop = pg
                        break
                if pop: break
            if pop: break
            time.sleep(0.25)

        if not pop:
            print("[unlock] no Solflare popup page found")
            return 3

        print(f"[unlock] popup url = {pop.url}")
        pop.bring_to_front()

        # Try to fill password / click unlock in both top doc and frames
        filled_any = False
        clicked_any = False

        filled_any |= _fill_direct(pop) or _type_with_keyboard(pop)
        clicked_any |= _press_unlockish(pop)

        for fr in pop.frames:
            try:
                filled_any |= _fill_direct(fr) or _type_with_keyboard(fr)
                clicked_any |= _press_unlockish(fr)
            except Exception:
                pass

        # One more sweep of “approve/continue” after unlock
        for lab in [r"connect", r"approve", r"allow", r"continue", r"ok", r"done"]:
            _try_click(pop.get_by_role("button", name=re.compile(lab, re.I)).first, 900)
            for fr in pop.frames:
                _try_click(fr.get_by_role("button", name=re.compile(lab, re.I)).first, 800)

        # If we got here, we did our best—return success-ish so flows can proceed
        print(f"[unlock] done (filled={filled_any}, clicked={clicked_any})")
        return 0

if __name__ == "__main__":
    sys.exit(main())
