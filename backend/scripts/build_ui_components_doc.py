from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "spec" / "ui.manifest.yaml"
OUT = ROOT / "docs" / "spec" / "ui_components.md"

def _now_iso_pt() -> str:
    # Timestamp for readability (PT hint; doesn't change TZ)
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _rel_module_path(file_path: str) -> str:
    """
    Convert 'frontend/src/foo/bar/Baz.jsx' -> 'foo/bar/Baz'
    (You can swap to alias import like '@/foo/bar/Baz' if your Vite alias is set.)
    """
    p = file_path.replace("\\", "/")
    if p.startswith("frontend/src/"):
        p = p[len("frontend/src/"):]
    return p.rsplit(".", 1)[0]

def _jsx_default_for_type(t: str) -> str:
    t = (t or "").lower()
    if t in ("string", "reactnode", "node", "element", "jsx.element"):
        return '"example"'
    if t in ("number", "int", "float"):
        return "{0}"
    if t in ("boolean", "bool"):
        return "{false}"
    if t in ("array", "any[]", "unknown[]", "string[]", "number[]"):
        return "{[]}"
    if t in ("object", "record", "map", "dict", "unknown", "any"):
        return "{{}}"
    # fallback
    return "{/* TODO */}"

def _jsx_prop_line(p: Dict[str, Any]) -> str:
    name = p.get("name", "prop")
    typ = p.get("type", "any")
    sample = _jsx_default_for_type(typ)
    return f'    {name}={sample}'

def _jsx_snippet(name: str, file_path: str, props: List[Dict[str, Any]]) -> str:
    mod = _rel_module_path(file_path) if file_path else "PATH/TO/COMPONENT"
    # Prefer named import that matches component name. Many codebases default-export; caller can tweak.
    lines = [
        f'// Adjust import per your alias setup (e.g., "@/...")',
        f'import {name} from "{mod}";',
        "",
        "export default function Example() {",
        "  return (",
        f"    <{name}",
    ]
    for p in props[:6]:  # keep snippet compact
        lines.append(_jsx_prop_line(p))
    lines.append(f"    />")
    lines.append("  );")
    lines.append("}")
    return "\n".join(lines)

def _props_table(props: List[Dict[str, Any]]) -> str:
    if not props:
        return "_No props documented._"
    rows = ["| Prop | Type | Required | Default |",
            "|------|------|----------|---------|"]
    for p in props:
        name = p.get("name", "")
        typ = p.get("type", "any")
        req = "yes" if p.get("required") else "no"
        default = p.get("default", "—")
        rows.append(f"| `{name}` | `{typ}` | {req} | {default} |")
    return "\n".join(rows)

def _markdown_header() -> str:
    return f"""# Sonic UI Components — Catalog (auto-generated)

> Source of truth: `docs/spec/ui.manifest.yaml`  
> Generated: {_now_iso_pt()}

Use this catalog to discover components, props, and example usage.  
To regenerate: `python backend/scripts/build_ui_components_doc.py`
"""

def _used_by_routes(name: str, file_path: str, routes: List[Dict[str, Any]]) -> List[str]:
    used: List[str] = []
    lname = (name or "").lower()
    for r in routes:
        comp = (r.get("component") or "").lower()
        rfile = (r.get("file") or "").replace("\\", "/")
        if comp == lname or (file_path and rfile == file_path.replace("\\", "/")):
            p = r.get("path", "")
            used.append(p or "(unnamed)")
    return sorted(set(used))

def main() -> None:
    if not MANIFEST.exists():
        raise SystemExit(f"missing manifest: {MANIFEST}")

    m = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    comps: List[Dict[str, Any]] = m.get("components") or []
    routes: List[Dict[str, Any]] = m.get("routes") or []

    # Sort by component name for stable output
    comps_sorted = sorted(comps, key=lambda c: (c.get("name") or c.get("id") or "").lower())

    parts: List[str] = [_markdown_header(), "## Table of contents"]
    for c in comps_sorted:
        anchor = (c.get("name") or c.get("id") or "COMP").lower()
        parts.append(f"- [{c.get('name') or c.get('id')}](#{anchor})")
    parts.append("")

    for c in comps_sorted:
        cid = c.get("id", "")
        name = c.get("name") or cid
        file_path = c.get("file", "")
        props: List[Dict[str, Any]] = c.get("props") or []
        used_routes = _used_by_routes(c.get("name") or "", file_path, routes)

        parts.append(f"## {name} (`{cid}`)")
        if file_path:
            parts.append(f"- **File**: `{file_path}`")
        if used_routes:
            parts.append(f"- **Used by routes**: {', '.join(f'`{p}`' for p in used_routes)}")
        else:
            parts.append(f"- **Used by routes**: _not referenced directly by a route_")

        parts.append("\n**Props**")
        parts.append(_props_table(props))
        parts.append("\n**Example**")
        snippet = _jsx_snippet(name, file_path, props)
        parts.append("```jsx\n" + snippet + "\n```")
        parts.append("---")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    print(f"[build_ui_components_doc] wrote {OUT}")

if __name__ == "__main__":
    main()
