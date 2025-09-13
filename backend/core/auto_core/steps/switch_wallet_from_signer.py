# file: auto_core/steps/switch_wallet_from_signer.py
import os, re, json, time, socket, base64
from typing import Optional, Tuple
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

PORT   = int(os.getenv("SONIC_CHROME_PORT", "9230"))
TARGET = os.getenv("SONIC_JUPITER_URL", "https://jup.ag/perps")
PASS   = (os.getenv("SOLFLARE_PASS") or "1492braxx").strip()
SIGNER_PATH = os.getenv("SONIC_SIGNER_PATH", r"C:\sonic5\signer.txt").strip()

# --------------------------
# Helpers: Chrome/Jupiter
# --------------------------
def _port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def _pick_jup_page(browser):
    # Prefer an existing jup.ag tab, else open one
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if "jup.ag" in (pg.url or ""):
                return pg
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    pg = ctx.new_page()
    pg.goto(TARGET, wait_until="domcontentloaded")
    return pg

def _button_not_visible(page) -> bool:
    # Return True if "Connect" button is NOT visible (assume already connected)
    try:
        page.get_by_role("button", name=re.compile(r"connect", re.I)).first.wait_for(state="visible", timeout=1200)
        return False
    except Exception:
        return True

def _open_connect_modal(page) -> bool:
    # Try to open the Connect modal; tolerate stale modals
    try:
        stale = page.get_by_role("dialog").first
        if stale:
            try:
                stale.get_by_role("button", name=re.compile(r"(close|×|x)", re.I)).first.click(timeout=400)
                time.sleep(0.2)
            except Exception:
                pass
    except Exception:
        pass
    for attempt in range(2):
        try:
            page.get_by_role("button", name=re.compile(r"connect", re.I)).first.click(timeout=2500)
        except Exception:
            time.sleep(0.2)
        # did a dialog appear?
        try:
            dlg = page.get_by_role("dialog").first
            dlg.wait_for(state="visible", timeout=1000)
            return True
        except Exception:
            pass
    return False

def _connect_modal(page):
    try:
        dlg = page.get_by_role("dialog").first
        dlg.wait_for(state="visible", timeout=1500)
        return dlg
    except Exception:
        return None

def _find_extension_page(browser, timeout_ms: int = 7000):
    """Return the Solflare extension window/page if it appears."""
    deadline = time.time() + (timeout_ms / 1000.0)
    # quick scan
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if (pg.url or "").startswith("chrome-extension://"):
                return pg
    # poll
    while time.time() < deadline:
        for ctx in browser.contexts:
            for pg in ctx.pages:
                if (pg.url or "").startswith("chrome-extension://"):
                    return pg
            try:
                new_pg = ctx.wait_for_event("page", timeout=250)
                if (new_pg.url or "").startswith("chrome-extension://"):
                    return new_pg
            except Exception:
                pass
        time.sleep(0.1)
    return None

def _click_solflare_in_modal(page) -> bool:
    dlg = _connect_modal(page)
    if not dlg:
        return False
    # Prefer "Recently Used" Solflare
    try:
        ru_label = dlg.get_by_text(re.compile(r"Recently Used", re.I)).first
        ru_label.wait_for(state="visible", timeout=1000)
        ru = ru_label.locator("xpath=ancestor::div[1]")
    except Exception:
        ru = dlg
    # Big tile candidates
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
                area = box["width"] * box["height"]
                if box["width"] >= 48 and box["height"] >= 48 and area >= 2400:
                    cands.append((area, el))
            except Exception:
                pass
    if cands:
        cands.sort(key=lambda t: t[0], reverse=True)
        try:
            cands[0][1].click(timeout=1200)
            return True
        except Exception:
            pass
    # Fallback list
    try:
        dlg.get_by_text(re.compile(r"View More Wallets", re.I)).first.click(timeout=1200)
        time.sleep(0.2)
    except Exception:
        pass
    for lab in [r"Standard", r"I already have a wallet", r"Wallets"]:
        try:
            dlg.get_by_text(re.compile(lab, re.I)).first.click(timeout=800)
            time.sleep(0.1)
        except Exception:
            pass
    for pat in [r"Solflare.*Extension", r"Solflare"]:
        try:
            dlg.get_by_role("button", name=re.compile(pat, re.I)).first.click(timeout=1500)
            return True
        except Exception:
            pass
    return False

# --------------------------
# Helpers: signer parsing
# --------------------------
def _read_signer(path: str) -> Tuple[str, str]:
    """
    Return (mode, payload) where mode in {"mnemonic","json","base58"}.
    Raises on missing/empty file.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"signer file not found: {path}")
    raw = open(path, "r", encoding="utf-8").read().strip()

    # JSON array of numbers? (phantom/solana-keygen export)
    try:
        j = json.loads(raw)
        if isinstance(j, list) and all(isinstance(x, int) for x in j):
            return "json", raw
    except Exception:
        pass

    # Looks like mnemonic? (>=12 words)
    words = re.findall(r"[a-z]+", raw.lower())
    if len(words) >= 12:
        return "mnemonic", " ".join(words)

    # Fallback: treat as base58 private key string (or raw secret)
    return "base58", raw

# --------------------------
# Solflare import/switch UI
# --------------------------
def _unlock_if_needed(pop):
    try:
        pop.locator('[data-testid="form-unlock"]').wait_for(state="visible", timeout=2500)
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

def _open_add_wallet(pop) -> bool:
    # Try common entry points
    for sel in [
        '[data-testid="btn-add-wallet"]',
        '[data-testid="add-wallet"]',
    ]:
        try:
            pop.locator(sel).first.click(timeout=800)
            time.sleep(0.2)
            return True
        except Exception:
            pass
    # Try hamburger/menu -> Add/Import
    for btn_pat in [r"(menu|settings|more)", r"(account|wallet)s?", r"manage"]:
        try:
            pop.get_by_role("button", name=re.compile(btn_pat, re.I)).first.click(timeout=800)
            time.sleep(0.2)
        except Exception:
            pass
    for txt in [r"Add wallet", r"Add account", r"Import wallet", r"I already have a wallet", r"Recover wallet"]:
        try:
            pop.get_by_text(re.compile(txt, re.I)).first.click(timeout=1000)
            time.sleep(0.2)
            return True
        except Exception:
            pass
    return False

def _choose_import_mode(pop, mode: str) -> bool:
    # Select import type
    if mode == "mnemonic":
        for t in [r"(Secret Recovery Phrase|Mnemonic)", r"Phrase", r"Seed"]:
            try:
                pop.get_by_text(re.compile(t, re.I)).first.click(timeout=800)
                time.sleep(0.2)
                return True
            except Exception:
                pass
    else:  # json/base58 -> Private key path
        for t in [r"Private Key", r"Raw Key", r"Import private key"]:
            try:
                pop.get_by_text(re.compile(t, re.I)).first.click(timeout=800)
                time.sleep(0.2)
                return True
            except Exception:
                pass
    return False

def _paste_secret(pop, mode: str, payload: str) -> bool:
    # Try common input areas
    for sel in ['textarea', 'input[type="text"]', 'input[autocomplete="one-time-code"]']:
        try:
            box = pop.locator(sel).first
            box.wait_for(state="visible", timeout=1000)
            box.click(timeout=600)
            box.fill(payload, timeout=1500)
            time.sleep(0.2)
            break
        except Exception:
            continue
    # Click continue/import/recover
    for lab in [r"(Continue|Import|Recover|Next|Add)"]:
        try:
            pop.get_by_role("button", name=re.compile(lab, re.I)).first.click(timeout=1200)
            time.sleep(0.6)
            return True
        except Exception:
            pass
    return False

def _finalize_and_connect(pop):
    # Approve/Connect flows if prompted
    for lab in [r"connect", r"approve", r"allow", r"continue", r"ok", r"done", r"finish"]:
        try:
            pop.get_by_role("button", name=re.compile(lab, re.I)).first.click(timeout=800)
            time.sleep(0.2)
        except Exception:
            pass

def main():
    if not _port_open(PORT):
        print(f"[switch] Chrome port {PORT} is not open")
        return 11

    mode, payload = _read_signer(SIGNER_PATH)
    print(f"[switch] signer mode detected: {mode}")

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
        page = _pick_jup_page(browser)

        # Ensure perps page, then open the Connect modal to trigger the extension popup
        try:
            if "/perps" not in (page.url or ""):
                page.goto(TARGET, wait_until="domcontentloaded")
        except Exception:
            pass

        if not _open_connect_modal(page):
            print("[switch] could not open Connect modal")
            return 12

        if not _click_solflare_in_modal(page):
            print("[switch] could not click Solflare in modal")
            return 2

        pop = _find_extension_page(browser, timeout_ms=9000)
        if not pop:
            print("[switch] Solflare popup not found")
            return 3

        pop.bring_to_front()
        _unlock_if_needed(pop)

        # Try to find an "Add/Import wallet/account" entry point
        if not _open_add_wallet(pop):
            # If adding is tucked behind a secondary screen, click typical "Accounts" / profile
            for txt in [r"Accounts", r"Wallets", r"Manage", r"Profile"]:
                try:
                    pop.get_by_text(re.compile(txt, re.I)).first.click(timeout=800)
                    time.sleep(0.2)
                    if _open_add_wallet(pop):
                        break
                except Exception:
                    pass

        # Choose import path & paste the secret/mnemonic
        if not _choose_import_mode(pop, mode):
            print("[switch] could not select import mode")
            return 5
        if not _paste_secret(pop, mode, payload):
            print("[switch] failed to paste secret/mnemonic or continue")
            return 6

        # Finalize: accept any prompts and ensure Jupiter shows as connected
        _finalize_and_connect(pop)
        time.sleep(0.8)

        if _button_not_visible(page):
            print("[switch] success (connected, connect button hidden)")
            return 0

        print("[switch] finished import/switch, but connection not verified")
        return 7

if __name__ == "__main__":
    import sys
    sys.exit(main())
