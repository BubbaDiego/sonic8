from __future__ import annotations
from pathlib import Path
import sys, re, yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "spec" / "ui.manifest.yaml"

def _err(errors, msg): 
    print("❌", msg); errors.append(msg)

def _ok(msg): 
    print("✅", msg)

def _exists(p: str) -> bool:
    return (ROOT / p).exists()

def _comp_name_from_id(comp_id: str) -> str:
    # COMP-FOO_BAR -> FOO_BAR
    return re.sub(r"^COMP-", "", comp_id or "", flags=re.I)

def main() -> int:
    errors: list[str] = []

    if not MANIFEST.exists():
        _err(errors, f"Missing manifest: {MANIFEST}")
        return 1

    try:
        m = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    except Exception as e:
        _err(errors, f"Could not parse manifest YAML: {e}")
        return 1

    fe = m.get("frontend") or {}
    entry = fe.get("entry")
    if entry:
        if _exists(entry):
            _ok(f"frontend.entry exists: {entry}")
        else:
            _err(errors, f"frontend.entry missing on disk: {entry}")
    else:
        _err(errors, "frontend.entry not set in manifest")

    # Build component index from manifest
    comps = m.get("components") or []
    comp_by_name: dict[str, dict] = {}
    for c in comps:
        cid = c.get("id") or ""
        name = c.get("name") or _comp_name_from_id(cid)
        file = c.get("file")
        if not file:
            _err(errors, f"component {cid or name} missing 'file' field")
            continue
        if not _exists(file):
            _err(errors, f"component file does not exist: {file} ({cid or name})")
        else:
            _ok(f"component file OK: {file}")
        comp_by_name[name] = c

    # Validate routes
    routes = m.get("routes") or []
    if not isinstance(routes, list):
        _err(errors, "routes must be a list")
        routes = []

    for r in routes:
        path = r.get("path")
        if not path or not isinstance(path, str) or not path.startswith("/"):
            _err(errors, f"route path invalid: {path!r}")
        else:
            _ok(f"route path OK: {path}")

        comp = r.get("component")
        if comp:
            # component refers to PascalCase component name
            c = comp_by_name.get(comp)
            if not c:
                _err(errors, f"route {path} references missing component: {comp}")
        f = r.get("file")
        if f:
            if not _exists(f):
                _err(errors, f"route {path} component file does not exist: {f}")
            else:
                _ok(f"route {path} file OK: {f}")

        shot = r.get("screenshot")
        if shot:
            # screenshots are optional; warn if missing
            if not _exists(shot):
                print(f"⚠️ screenshot not found (optional): {shot}")

    if errors:
        print("\n=== UI manifest validation FAILED ===")
        for e in errors: print(" -", e)
        return 1

    print("\n=== UI manifest validation OK ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
