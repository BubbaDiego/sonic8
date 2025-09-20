from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Iterable

import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "spec" / "spec.manifest.yaml"


def load_app():
    """Import the FastAPI app from known entrypoints."""

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "backend"))
    errors: list[str] = []
    for module_name, attr in [("backend.sonic_backend_app", "app"), ("backend.main", "app")]:
        try:
            module = importlib.import_module(module_name)
            return getattr(module, attr)
        except Exception as exc:  # pragma: no cover - diagnostic output
            errors.append(f"{module_name}: {exc}")
    for err in errors:
        print(f"[spec_api_mapper] failed to import {err}")
    raise SystemExit("Couldn't import FastAPI app")


def http_methods(route_methods: Iterable[str] | None) -> list[str]:
    return [
        method.lower()
        for method in (route_methods or [])
        if method in {"GET", "POST", "PUT", "DELETE", "PATCH"}
    ]


def main():
    app = load_app()
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    apis = manifest.get("apis") or []
    existing = {(api.get("method", "").lower(), api.get("path", "")) for api in apis}
    changed = False

    for route in app.routes:
        try:
            path = route.path
            methods = http_methods(route.methods)
        except Exception:
            continue

        for method in methods:
            if path.startswith(("/docs", "/openapi", "/redoc")):
                continue
            key = (method, path)
            if key in existing:
                continue

            apis.append(
                {
                    "id": f"API-{method}-{path.strip('/').replace('/', '_') or 'root'}",
                    "type": "http",
                    "method": method.upper(),
                    "path": path,
                    "response_schema": None,
                }
            )
            changed = True

    if changed:
        manifest["apis"] = apis
        MANIFEST.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
        print("[spec_api_mapper] added new API entries.")
    else:
        print("[spec_api_mapper] no new routes to add.")


if __name__ == "__main__":
    main()
