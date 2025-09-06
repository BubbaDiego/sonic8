import os, re, sys, time
from typing import Optional
from playwright.sync_api import sync_playwright

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
    Return the asset chip from the top-left chips row (SOL / ETH / WBTC).
    Strategy:
      1) Prefer role=tab with exact name (common in top chip row).
      2) Otherwise, collect all elements named <symbol> near the top bar,
         filter out tiny controls (token pickers), and choose the one
         that updates aria-selected after click.
    """
    # 1) Try role=tab first — usually the chip row
    try:
        tab = page.get_by_role("tab", name=re.compile(rf"^{symbol}$", re.I)).first
        # Accessing its bbox ensures it exists
        if tab.bounding_box():
            return tab
    except Exception:
        pass

    # 2) Heuristic collection near the top bar
    possibles = []
    for loc in [
        page.get_by_role("button", name=re.compile(rf"^{symbol}$", re.I)),
        page.get_by_text(re.compile(rf"^\s*{symbol}\s*$", re.I)),
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
                # Near top-left chip row; large enough to be a chip
                if (
                    box["y"] < 180
                    and box["x"] < 320
                    and box["width"] >= 44
                    and box["height"] >= 24
                ):
                    possibles.append(el)
            except Exception:
                pass
    # Return the first viable candidate
    return possibles[0] if possibles else None

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

        # Ensure we're on the perps page
        try:
            if "/perps" not in (page.url or ""):
                page.goto(TARGET, wait_until="domcontentloaded")
        except Exception:
            pass

        # Try up to 3 candidates; verify aria-selected flips true
        attempts = 0
        tried = set()
        while attempts < 3:
            btn = _find_asset_button(page, symbol)
            if not btn:
                print(f"[asset] chip not found for '{symbol}' (attempt {attempts+1})")
                attempts += 1
                time.sleep(0.25)
                continue
            # Avoid re-clicking the same underlying handle
            try:
                key = btn.bounding_box() or {"x":0,"y":0}
                key = (round(key["x"]), round(key["y"]))
            except Exception:
                key = (attempts, 0)
            if key in tried:
                attempts += 1
                continue
            tried.add(key)

            if not _try_locator_click(page, btn, timeout=2000):
                print(f"[asset] click failed on candidate at {key}")
                attempts += 1
                continue

            time.sleep(0.4)
            # Verify aria-selected becomes true
            try:
                sel = btn.get_attribute("aria-selected")
                if sel and sel.lower() == "true":
                    print(f"[asset] selected {symbol}")
                    return 0
            except Exception:
                pass

            print(f"[asset] candidate at {key} did not become selected; retrying")
            attempts += 1

        print(f"[asset] failed to select {symbol}")
        return 4

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=False)
    a = ap.parse_args()
    sys.exit(main(a.symbol))
