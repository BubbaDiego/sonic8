from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"
for candidate in (str(ROOT), str(BACKEND_DIR)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from backend.sonic_backend_app import app


def main():
    from fastapi.openapi.utils import get_openapi
    try:
        from yaml import safe_dump
    except ImportError:  # pragma: no cover - executed only when PyYAML missing
        raise SystemExit("Please `pip install pyyaml`")

    schema = get_openapi(
        title=getattr(app, "title", "Sonic API"),
        version="v1",
        routes=app.routes,
    )
    out_path = Path("backend/api/openapi.yaml")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        safe_dump(schema, f, sort_keys=False)
    print(f"[export_openapi] wrote {out_path}")


if __name__ == "__main__":
    main()
