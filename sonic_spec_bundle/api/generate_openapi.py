#!/usr/bin/env python3
"""
Exports FastAPI OpenAPI spec to api/openapi.yaml
Assumes your FastAPI app is exposed as `app` in api/main.py (adjust import if needed).
"""
from __future__ import annotations
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from api.main import app  # e.g., api/main.py -> app = FastAPI(...)
except Exception as e:
    raise SystemExit(f"Could not import FastAPI app: {e}")

OUT = ROOT / "api" / "openapi.yaml"

def main():
    spec = app.openapi()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
