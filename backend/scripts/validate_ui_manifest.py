from __future__ import annotations
from pathlib import Path
import sys, re, yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "spec" / "ui.manifest.yaml"

BUILTINS = {"navigate", "outlet", "suspense", "fragment"}  # react-router / react built-ins


def _safe_print(sym_utf8: str, ascii_fallback: str, msg: str):
    try:
        print(sym_utf8, msg)
    except UnicodeEncodeError:
        print(ascii_fallback, msg)


def _err(errors, msg):
    _safe_print("\u274C", "[FAIL]", msg); errors.append(msg)  # ❌


def _warn(msg):
    _safe_print("\u26A0\uFE0F", "[WARN]", msg)  # ⚠️


def _ok(msg):
    _safe_print("\u2705", "[OK]", msg)  # ✅

def _exists(p: str) -> bool:
    return bool(p) and (ROOT / p).exists()

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

    # ----- FRONTEND ENTRY -----
    fe = m.get("frontend") or {}
    entry = fe.get("entry")
    if entry and _exists(entry):
        _ok(f"frontend.entry exists: {entry}")
    else:
        _err(errors, f"frontend.entry missing on disk: {entry}")

    # ----- COMPONENT INDEX (case-insensitive) -----
    comps = m.get("components") or []
    comp_by_name_ci: dict[str, dict] = {}
    for c in comps:
        # Prefer explicit "name", else derive from id
        name = (c.get("name") or re.sub(r"^COMP-", "", c.get("id") or "", flags=re.I)).strip()
        if not name:
            _warn(f"component missing name/id: {c}")
            continue
        file = c.get("file")
        if not file or not _exists(file):
            _err(errors, f"component file missing on disk: {file} ({name})")
        else:
            _ok(f"component file OK: {file}")
        comp_by_name_ci[name.lower()] = c

    # ----- ROUTES -----
    routes = m.get("routes") or []
    if not isinstance(routes, list):
        _err(errors, "routes must be a list")
        routes = []

    for r in routes:
        path = r.get("path")
        if not path or not isinstance(path, str):
            _err(errors, f"route path invalid: {path!r}")
            continue

        # Accept wildcard and nested (relative) paths with warnings instead of errors
        if path == "*":
            _warn("route path is wildcard '*' (accepted)")
        elif not path.startswith("/"):
            _warn(f"route path is relative (nested): {path!r} (accepted)")
        else:
            _ok(f"route path OK: {path}")

        comp = (r.get("component") or "").strip()
        file = r.get("file")

        # If a built-in like Navigate/Outlet, skip component existence check
        if comp and comp.lower() in BUILTINS:
            _warn(f"route {path} uses built-in component {comp} (skipped)")
        elif comp:
            # lookup case-insensitive
            if comp.lower() not in comp_by_name_ci:
                # If file exists we still consider it OK-ish; warn instead of failing hard
                if file and _exists(file):
                    _warn(f"route {path} references component {comp} not in manifest components list, but file exists: {file}")
                else:
                    _err(errors, f"route {path} references missing component: {comp}")

        # file check (optional)
        if file:
            if _exists(file):
                _ok(f"route {path} file OK: {file}")
            else:
                _err(errors, f"route {path} component file does not exist: {file}")

        # optional screenshot
        shot = r.get("screenshot")
        if shot and not _exists(shot):
            _warn(f"screenshot missing (optional): {shot}")

    if errors:
        print("\n=== UI manifest validation FAILED ===")
        for e in errors: print(" -", e)
        return 1

    print("\n=== UI manifest validation OK ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
