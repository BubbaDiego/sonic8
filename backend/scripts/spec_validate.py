from __future__ import annotations

import glob
import json
import os
import sys
from pathlib import Path

import yaml
try:
    from jsonschema import Draft2020Validator
except ImportError:
    from jsonschema import Draft202012Validator as Draft2020Validator


def validate_schemas() -> bool:
    ok = True
    for path_str in glob.glob("docs/spec/schemas/*.json"):
        path = Path(path_str)
        try:
            with path.open("r", encoding="utf-8") as fh:
                Draft2020Validator.check_schema(json.load(fh))
            print("OK", path)
        except Exception as exc:  # noqa: BLE001 - we want to surface jsonschema errors
            ok = False
            print("ERR", path, exc)
    return ok


def validate_manifest() -> bool:
    manifest_path = Path("docs/spec/spec.manifest.yaml")
    with manifest_path.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)

    repo_root = manifest_path.parents[2]

    def check(path: str | None) -> bool:
        if not path or not isinstance(path, str):
            return False
        if path.startswith(('http://', 'https://', '/')):
            return True
        candidate = repo_root / path
        return candidate.exists()

    ok = True
    for section in ("modules", "apis", "schemas"):
        for item in manifest.get(section) or []:
            ref_path = item.get("path")
            if ref_path and not check(ref_path):
                ok = False
                print("MISSING", section, ref_path)
    return ok


def main() -> int:
    ok = validate_schemas()
    ok &= validate_manifest()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
