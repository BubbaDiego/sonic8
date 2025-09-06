import os, re, sys, time
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

PORT   = int(os.getenv("SONIC_CHROME_PORT", "9230"))
TARGET = os.getenv("SONIC_JUPITER_URL", "https://jup.ag/perps")

def _norm_symbol(sym: str) -> str:
    sym = (sym or "").strip().upper()
    if sym in ("BTC", "WBTC"): return "WBTC"
    if sym in ("ETH",):        return "ETH"
    # default to SOL if not recognized
    return "SOL"

def _pick_jup_page(browser):
    # Prefer an already-open jup.ag tab
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if "jup.ag" in (pg.url or ""):
                return pg
    # Otherwise open one
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    pg = ctx.new_page()
    pg.goto(TARGET, wait_until="domcontentloaded")
    return pg

def _try_locator_click(page, locator, timeout=1500) -> bool:
    try:
        locator.wait_for(state="visible", timeout=timeout)
        locator.click(timeout=timeout)
        return True
    except Exception:
        return False

def _find_asset_button(page, symbol: str):
    """
    Return the asset chip at the very top-left of the Perps page.
    We gather all visible elements named <symbol> and choose the one
    whose bounding box is closest to the top-left and reasonably sized.
    """
    candidates = []
    locators = [
        page.get_by_role("tab",    name=re.compile(rf"^{symbol}$", re.I)),
        page.get_by_role("button", name=re.compile(rf"^{symbol}$", re.I)),
        page.get_by_text(re.compile(rf"^\s*{symbol}\s*$", re.I)),
    ]
    for loc in locators:
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
                # Heuristics for the top-left chips row
                if box["y"] < 180 and box["x"] < 280 and box["width"] >= 36 and box["height"] >= 24:
                    candidates.append((box["x"] + box["y"], el))  # “distance” from origin
            except Exception:
                pass
    if not candidates:
        return None
    # Choose the closest-to-origin candidate
    candidates.sort(key=lambda t: t[0])
    return candidates[0][1]

def _is_selected(el) -> bool:
    try:
        sel = el.get_attribute("aria-selected")
        if sel and sel.lower() == "true":
            return True
    except Exception:
        pass
    try:
        ds = el.get_attribute("data-state")
        if ds and ds.lower() in ("active", "on", "selected"):
            return True
    except Exception:
        pass
    try:
        cls = el.get_attribute("class") or ""
        if re.search(r"(active|selected)", cls, re.I):
            return True
    except Exception:
        pass
    return False

def main(symbol: Optional[str] = None):
    symbol = _norm_symbol(symbol or os.getenv("SONIC_ASSET", "SOL"))

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
        page = _pick_jup_page(browser)

        # Make sure the page is up
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass

        btn = _find_asset_button(page, symbol)
        if not btn:
            print(f"[asset] could not find asset chip for '{symbol}'")
            return 2

        # Click the asset chip
        if not _try_locator_click(page, btn, timeout=2000):
            print(f"[asset] failed to click asset chip '{symbol}'")
            return 3

        # Small settle; then verify it's selected
        time.sleep(0.4)
        # Re-locate to avoid stale reference
        btn2 = _find_asset_button(page, symbol) or btn
        if _is_selected(btn2):
            print(f"[asset] selected {symbol}")
            return 0

        # Some UIs don't expose selection state; fall back to OK after click
        print(f"[asset] clicked {symbol} (selection state not exposed)")
        return 0

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=False)
    a = ap.parse_args()
    sys.exit(main(a.symbol))
