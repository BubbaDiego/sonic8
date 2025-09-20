from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def say(level: str, message: str) -> None:
    print(f"[{level}] {message}")


def ensure_export_openapi() -> bool:
    say("RUN", "Ensuring OpenAPI export is up to date...")
    exporter = ROOT / "backend" / "scripts" / "export_openapi.py"
    if not exporter.exists():
        say("WARN", f"Exporter script missing: {exporter}")
        return False
    out = subprocess.run([sys.executable, str(exporter)], capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if out.returncode != 0:
        say("ERR", "OpenAPI export failed")
        if out.stdout:
            print(out.stdout.strip())
        if out.stderr:
            print(out.stderr.strip())
        return False
    say("OK", "OpenAPI export completed")
    if out.stdout:
        print(out.stdout.strip())
    if out.stderr:
        print(out.stderr.strip())
    return True


def ensure_markers_and_sweep() -> bool:
    say("RUN", "Ensuring spec markers and sweeper checks...")
    sweeper = ROOT / "backend" / "scripts" / "spec_sweeper.py"
    if not sweeper.exists():
        say("WARN", f"Spec sweeper script missing: {sweeper}")
        return False
    out = subprocess.run([sys.executable, str(sweeper)], capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if out.returncode != 0:
        say("ERR", "Spec sweeper failed")
        if out.stdout:
            print(out.stdout.strip())
        if out.stderr:
            print(out.stderr.strip())
        return False
    say("OK", "Spec sweeper completed")
    if out.stdout:
        print(out.stdout.strip())
    if out.stderr:
        print(out.stderr.strip())
    return True


def validate_schemas_and_manifest() -> bool:
    say("RUN", "Validating JSON schemas and manifest paths...")
    try:
        from jsonschema.validators import Draft202012Validator as _VAL
    except Exception:
        try:
            from jsonschema import Draft7Validator as _VAL  # type: ignore[assignment]
        except Exception as e:  # noqa: BLE001 - surface import errors
            say("WARN", f"jsonschema not installed or validator import failed: {e}")
            _VAL = None

    ok = True
    if _VAL is not None:
        for p in glob.glob(str(ROOT / "docs" / "spec" / "schemas" / "*.json")):
            try:
                _VAL.check_schema(json.load(open(p, encoding="utf-8")))
                print(f"   • schema OK {os.path.relpath(p, ROOT)}")
            except Exception as e:  # noqa: BLE001 - allow jsonschema exceptions to propagate info
                ok = False
                print(f"   • schema ERR {os.path.relpath(p, ROOT)} :: {e}")
        if ok:
            say("OK", "All JSON Schemas are structurally valid.")
        else:
            say("ERR", "One or more JSON Schemas are invalid.")

    manifest_path = ROOT / "docs" / "spec" / "spec.manifest.yaml"
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8") as fh:
            manifest = yaml.safe_load(fh) or {}
        repo_root = manifest_path.parents[2]

        def check(path: str | None) -> bool:
            if not path or not isinstance(path, str):
                return False
            if path.startswith(("http://", "https://", "/")):
                return True
            candidate = repo_root / path
            return candidate.exists()

        manifest_ok = True
        for section in ("modules", "apis", "schemas"):
            for item in manifest.get(section) or []:
                ref_path = item.get("path")
                if ref_path and not check(ref_path):
                    manifest_ok = False
                    print(f"   • manifest MISSING {section} {ref_path}")
        if manifest_ok:
            say("OK", "Manifest references are valid.")
        else:
            say("ERR", "Manifest references missing paths.")
            ok = False
    else:
        say("WARN", f"Manifest file not found: {manifest_path}")
        ok = False

    return ok


def main() -> int:
    status = True
    status &= ensure_export_openapi()
    status &= ensure_markers_and_sweep()
    status &= validate_schemas_and_manifest()
    return 0 if status else 1


if __name__ == "__main__":
    raise SystemExit(main())
