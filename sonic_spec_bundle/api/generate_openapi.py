#!/usr/bin/env python3
"""
Robust OpenAPI exporter for nested bundles.

Reads:
  SONIC_ROOT=C:\path\to\repo        (optional but recommended)
  SONIC_APP=package.module:app      (or package.module:create_app)

Examples:
  $env:SONIC_ROOT = 'C:\\sonic5'
  $env:SONIC_APP  = 'server.main:app'
  python api\\generate_openapi.py
"""
from __future__ import annotations
from pathlib import Path
import importlib, os, sys
import yaml

# --- Resolve repo root ---
env_root = os.environ.get("SONIC_ROOT")
if env_root:
    REPO_ROOT = Path(env_root).resolve()
else:
    # climb up to find a plausible repo root; prefer a parent with .git or pyproject.toml
    here = Path(__file__).resolve()
    candidates = list(here.parents)[:6]
    pick = None
    for cand in candidates:
        if (cand / ".git").exists() or (cand / "pyproject.toml").exists():
            pick = cand
            break
    REPO_ROOT = pick or here.parents[2]

# ensure we import from the real repo, not the bundle
sys.path.insert(0, str(REPO_ROOT))

target = os.environ.get("SONIC_APP", "api.main:app")

# --- helpers ---
def is_asgi_app(obj) -> bool:
    try:
        # Fast path: FastAPI/Starlette detection
        from fastapi import FastAPI  # type: ignore
        from starlette.applications import Starlette  # type: ignore
        if isinstance(obj, (FastAPI, Starlette)):
            return True
    except Exception:
        pass
    # heuristic: has router and openapi (FastAPI), or routes (Starlette)
    return hasattr(obj, "openapi") and hasattr(obj, "router") or hasattr(obj, "routes")

def load_app(spec: str):
    if ":" not in spec:
        raise SystemExit("SONIC_APP must look like 'package.module:app' or 'package.module:create_app'")
    mod_path, attr = spec.split(":", 1)
    mod = importlib.import_module(mod_path)
    obj = getattr(mod, attr)

    # If it's already an ASGI app (FastAPI/Starlette), DO NOT CALL IT
    if is_asgi_app(obj):
        return obj

    # Otherwise assume it's a factory and call it once
    if callable(obj):
        inst = obj()
        if is_asgi_app(inst):
            return inst

    raise SystemExit(f"{spec} did not resolve to a FastAPI/Starlette app or factory")

# --- load app and write spec ---
try:
    app = load_app(target)
except Exception as e:
    raise SystemExit(f"Failed to import FastAPI app from {target}: {e}")

try:
    route_count = len(getattr(app, "routes", []))
    print(f"Loaded {target} from {REPO_ROOT} with {route_count} routes")
except Exception:
    pass

spec = app.openapi()
out = REPO_ROOT / "api" / "openapi.yaml"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
print(f"Wrote {out}")
