from __future__ import annotations
import ast, os, re, sys, textwrap, yaml
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]  # repo root
SPEC_MD = ROOT / "docs" / "spec" / "software_spec.md"
MANIFEST = ROOT / "docs" / "spec" / "spec.manifest.yaml"

def load_manifest() -> Dict:
    with open(MANIFEST, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def list_key_files(module_path: Path, limit: int = 6) -> List[Path]:
    """Return top-level .py files + __init__.py + key submodule __init__.py (shallow)."""
    out: List[Path] = []
    if not module_path.exists():
        return out
    # priority: __init__.py + obvious entry points + up to 'limit' others
    candidates = []
    for p in sorted(module_path.iterdir()):
        if p.is_file() and p.suffix == ".py":
            candidates.append(p)
        elif p.is_dir():
            ip = p / "__init__.py"
            if ip.exists():
                candidates.append(ip)
    # Deduplicate and clip
    seen = set()
    for p in candidates:
        if len(out) >= limit:
            break
        if p.resolve() in seen:
            continue
        seen.add(p.resolve())
        out.append(p)
    return out

def _sig_from_def(node: ast.AST) -> str:
    if isinstance(node, ast.FunctionDef):
        args = [a.arg for a in node.args.args]
        return f"def {node.name}({', '.join(args)})"
    if isinstance(node, ast.AsyncFunctionDef):
        args = [a.arg for a in node.args.args]
        return f"async def {node.name}({', '.join(args)})"
    if isinstance(node, ast.ClassDef):
        return f"class {node.name}"
    return ""

def extract_public_signatures(py_file: Path, max_items: int = 6) -> List[str]:
    try:
        src = py_file.read_text("utf-8", errors="ignore")
        tree = ast.parse(src)
    except Exception:
        return []
    sigs: List[str] = []
    for node in tree.body:
        sig = _sig_from_def(node)
        if not sig:
            continue
        # skip private
        name = getattr(node, "name", "")
        if name.startswith("_"):
            continue
        sigs.append(sig)
        if len(sigs) >= max_items:
            break
    return sigs

def make_repo_map(modules: List[Dict]) -> str:
    rows = [
        "| ID | Path | Role | Notes |",
        "|---|---|---|---|",
    ]
    for m in modules:
        mid = m.get("id")
        path = m.get("path")
        role = m.get("purpose","")
        note = ""
        rows.append(f"| {mid} | `{path}` | {role} | {note} |")
    return "\n".join(rows)

def make_module_inventory(modules: List[Dict]) -> str:
    parts: List[str] = []
    for m in modules:
        mid = m.get("id")
        path = m.get("path")
        role = m.get("purpose","")
        p = ROOT / path
        files = list_key_files(p)
        display_files: List[str] = []
        for f in files:
            try:
                rel = f.relative_to(ROOT)
                display_files.append(rel.as_posix())
            except ValueError:
                display_files.append(f.as_posix())
        file_lines = [f"- `{path}`" for path in display_files] or ["- _(none found)_"]

        sig_lines: List[str] = []
        for f in files[:4]:
            sigs = extract_public_signatures(f, max_items=4)
            if sigs:
                sig_lines.append(f"  - **{f.name}**: " + "; ".join(sigs))
        if not sig_lines:
            sig_lines = ["  - _(no public signatures detected)_"]

        section = f"""
### {mid}
- **Path**: `{path}`
- **Purpose**: {role}
- **Key files**
{os.linesep.join(file_lines)}
- **Public interfaces (signatures)**
{os.linesep.join(sig_lines)}
"""
        parts.append(textwrap.dedent(section).strip())
    return "\n\n".join(parts)

def replace_block(text: str, begin: str, end: str, new_content: str) -> str:
    pattern = re.compile(rf"({re.escape(begin)})(.*?)(\s*{re.escape(end)})", re.DOTALL)
    repl = f"{begin}\n{new_content}\n{end}"
    if pattern.search(text):
        return pattern.sub(repl, text, count=1)
    # If markers not found, append at end
    return f"{text.rstrip()}\n\n{repl}\n"

def main(write: bool = True) -> None:
    mf = load_manifest()
    modules = mf.get("modules") or []
    # Only include modules that actually exist on disk
    exist = [m for m in modules if m.get("path") and (ROOT / m["path"]).exists()]
    repo_map_md = make_repo_map(exist)
    inventory_md = make_module_inventory(exist)

    md = SPEC_MD.read_text("utf-8")
    md = replace_block(md, "<!-- REPO_MAP:BEGIN -->", "<!-- REPO_MAP:END -->", repo_map_md)
    md = replace_block(md, "<!-- MODULE_INVENTORY:BEGIN -->", "<!-- MODULE_INVENTORY:END -->", inventory_md)
    if write:
        SPEC_MD.write_text(md, encoding="utf-8")
        print("[spec_sweeper] updated", SPEC_MD)
    else:
        print(md)

if __name__ == "__main__":
    # Usage: python backend/scripts/spec_sweeper.py
    main(write=True)
