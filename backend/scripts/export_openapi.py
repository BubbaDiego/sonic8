from __future__ import annotations
from pathlib import Path
import sys, importlib, os

os.environ.setdefault("EXPORT_OPENAPI", "1")

# Ensure repo root on sys.path when run as a script
ROOT = Path(__file__).resolve().parents[2]
for candidate in (ROOT, ROOT / "backend"):
    s = str(candidate)
    if s not in sys.path:
        sys.path.insert(0, s)

# Try likely app modules in order (first is Sonic's real app)
_CANDIDATES = [
    ("backend.sonic_backend_app", "app"),
    ("backend.main", "app"),  # fallback if present
]

errors = []
app = None
for mod_name, attr in _CANDIDATES:
    try:
        mod = importlib.import_module(mod_name)
    except Exception as exc:
        errors.append(f"{mod_name}: import failed ({exc})")
        continue
    try:
        app = getattr(mod, attr)
    except AttributeError as exc:
        errors.append(f"{mod_name}: missing attribute {attr} ({exc})")
        continue
    if app is not None:
        break

if app is None:
    msg = "; ".join(errors) if errors else "no candidates"
    tried = ", ".join(f"{m}:{a}" for m, a in _CANDIDATES)
    if os.environ.get("EXPORT_OPENAPI") == "1":
        print(f"[export_openapi] skipped ({msg})")
        raise SystemExit(0)
    raise SystemExit(f"Could not import FastAPI app. Tried: {tried}. Errors: {msg}")

from fastapi.openapi.utils import get_openapi
from yaml import safe_dump  # pip install pyyaml

schema = get_openapi(
    title=getattr(app, "title", "Sonic API"),
    version="v1",
    routes=app.routes,
)

out_path = ROOT / "backend" / "api" / "openapi.yaml"
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    safe_dump(schema, f, sort_keys=False)
print(f"[export_openapi] wrote {out_path}")
