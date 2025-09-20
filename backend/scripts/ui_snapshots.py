from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

import yaml
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "spec" / "ui.manifest.yaml"
OUTDIR = ROOT / "docs" / "spec" / "ui_shots"


def load_manifest() -> Dict[str, object]:
    if MANIFEST.exists():
        try:
            return yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}
    return {}


def safe_page_id(path: str) -> str:
    slug = path.strip()
    if not slug or slug == "/":
        slug = "root"
    slug = slug.strip("/") or "root"
    slug = "_".join(filter(None, slug.split("/"))) or "root"
    slug = slug.replace(" ", "-")
    return f"PAGE_{slug.upper()}"


def ensure_absolute_url(base_url: str, path: str) -> str:
    if not path.startswith("/"):
        path = f"/{path}"
    return base_url.rstrip("/") + path


def capture_routes(routes: List[Dict[str, object]], base_url: str) -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    if not routes:
        print("[ui_snapshots] no routes defined in manifest")
        return

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        for route in routes:
            path = route.get("path") or "/"
            page_id = route.get("page_id") or safe_page_id(path)
            url = ensure_absolute_url(base_url, path)
            print(f"[ui_snapshots] visiting {url}")
            page.goto(url, wait_until="networkidle")
            outfile = OUTDIR / f"{page_id}.png"
            page.screenshot(path=str(outfile), full_page=True)
            print(f"[ui_snapshots] saved {outfile.relative_to(ROOT)}")
        browser.close()


def main() -> None:
    manifest = load_manifest()
    routes = manifest.get("routes", [])  # type: ignore[assignment]
    frontend = manifest.get("frontend", {})  # type: ignore[assignment]
    base_url = os.getenv("UI_BASE_URL") or frontend.get("base_url_hint") or "http://127.0.0.1:5173"
    capture_routes(routes, base_url)


if __name__ == "__main__":
    main()
