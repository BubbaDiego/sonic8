from __future__ import annotations
import json
import glob
import os
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
import yaml

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "docs" / "spec" / "schemas"
MANIFEST = ROOT / "docs" / "spec" / "spec.manifest.yaml"


def validate_schemas() -> bool:
    ok = True
    for path in sorted(SCHEMA_DIR.glob("*.json")):
        try:
            Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:  # noqa: BLE001
            ok = False
            print(f"ERR {path}", exc)
        else:
            print(f"OK {path}")
    return ok


def validate_manifest() -> bool:
    ok = True
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    for section in ("modules", "apis", "schemas"):
        for item in data.get(section) or []:
            p = item.get("path")
            if p and not os.path.exists(p):
                ok = False
                print(f"MISSING {section} {p}")
    return ok


def main() -> int:
    schemas_ok = validate_schemas()
    manifest_ok = validate_manifest()
    return 0 if schemas_ok and manifest_ok else 1


if __name__ == "__main__":
    sys.exit(main())
