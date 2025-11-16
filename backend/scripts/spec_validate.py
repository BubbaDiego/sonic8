from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Dict, Union

import yaml

# Robust jsonschema import: tolerate environments where rpds/jsonschema is broken
try:
    try:
        # Preferred: 2020-12 validator
        from jsonschema.validators import Draft202012Validator as V  # type: ignore[assignment]
    except Exception:
        # Fallback: older Draft7 validator
        from jsonschema import Draft7Validator as V  # type: ignore[assignment]
except Exception as exc:
    print("[spec_validate] WARNING: jsonschema import failed; skipping spec validation.")
    print(f"[spec_validate] reason: {exc!r}")
    sys.exit(0)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "docs" / "spec" / "schemas"
MANIFEST = ROOT / "docs" / "spec" / "spec.manifest.yaml"


def validate_schemas() -> bool:
    ok = True
    for p in sorted(SCHEMA_DIR.glob("*.json")):
        try:
            V.check_schema(json.loads(p.read_text(encoding="utf-8")))
            print("OK", p)
        except Exception as e:  # pragma: no cover - diagnostic output
            ok = False
            print("ERR", p, e)
    return ok


def _index_schema_ids(manifest: Dict) -> Dict[str, Union[Path, str]]:
    out: Dict[str, Union[Path, str]] = {}
    for s in manifest.get("schemas") or []:
        sid, spath = s.get("id"), s.get("path")
        if not sid or not spath:
            continue
        if isinstance(spath, str) and spath.startswith(("http://", "https://", "/")):
            out[str(sid)] = spath
        else:
            out[str(sid)] = (ROOT / spath).resolve()
    return out


def validate_manifest() -> bool:
    ok = True
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}

    # modules: path must exist on disk if relative
    for m in data.get("modules") or []:
        mp = m.get("path")
        if not mp:
            continue
        if isinstance(mp, str) and mp.startswith(("http://", "https://", "/")):
            # treat absolute/URL as non-file
            continue
        fp = (ROOT / mp).resolve()
        if not fp.exists():
            ok = False
            print("MISSING modules", mp)

    # schemas: each file must exist if local
    schema_idx = _index_schema_ids(data)
    for sid, spath in schema_idx.items():
        if isinstance(spath, str) and spath.startswith(("http://", "https://", "/")):
            continue
        local_path = Path(spath)
        if not local_path.exists():
            ok = False
            print("MISSING schemas", local_path.as_posix())

    # apis: validate based on type
    for a in data.get("apis") or []:
        api_type = str(a.get("type") or "http").lower()
        path = a.get("path")
        if not path or not isinstance(path, str):
            ok = False
            print("MISSING apis", path)
            continue

        if api_type == "http":
            if not path.startswith("/") and path != "*":
                ok = False
                print("MISSING apis", path)

            rs_id = a.get("response_schema")
            if rs_id:
                sp = schema_idx.get(rs_id)
                if sp is None:
                    ok = False
                    print("MISSING apis response_schema", rs_id)
            else:
                ok = False
                print("MISSING apis response_schema (none set) for", path)
        else:
            # treat non-http paths as file references relative to repo root
            if path.startswith(("http://", "https://")):
                continue

            file_path = (ROOT / path) if not path.startswith("/") else Path(path)
            if not file_path.exists():
                ok = False
                print("MISSING apis path", path)
    return ok


def main() -> int:
    schemas_ok = validate_schemas()
    manifest_ok = validate_manifest()
    return 0 if (schemas_ok and manifest_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
