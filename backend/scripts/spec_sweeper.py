from __future__ import annotations
import ast
import yaml
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
SPEC_MD = ROOT / "docs" / "spec" / "software_spec.md"
MANIFEST = ROOT / "docs" / "spec" / "spec.manifest.yaml"

def load_manifest() -> Dict:
    with open(MANIFEST, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def list_key_files(module_path: Path, limit: int = 6) -> List[Path]:
    out: List[Path] = []
    if not module_path.exists():
        return out
    candidates = []
    for p in sorted(module_path.iterdir()):
        if p.is_file() and p.suffix == ".py":
            candidates.append(p)
        elif p.is_dir() and (p / "__init__.py").exists():
            candidates.append(p / "__init__.py")
    seen = set()
    for p in candidates:
        if len(out) >= limit: break
        rp = p.resolve()
        if rp in seen: continue
        seen.add(rp)
        out.append(p)
    return out

def sigs_from_file(py_file: Path, max_items: int = 4) -> List[str]:
    try:
        tree = ast.parse(py_file.read_text("utf-8", errors="ignore"))
    except Exception:
        return []
    sigs: List[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name
            if name.startswith("_"): continue
            args = [a.arg for a in node.args.args]
            sigs.append(f"def {name}({', '.join(args)})")
        elif isinstance(node, ast.ClassDef):
            if node.name.startswith("_"): continue
            sigs.append(f"class {node.name}")
        if len(sigs) >= max_items: break
    return sigs

def build_repo_map(mods: List[Dict]) -> str:
    rows = ["| ID | Path | Role | Notes |", "|---|---|---|---|"]
    for m in mods:
        rows.append(f"| {m.get('id')} | `{m.get('path')}` | {m.get('purpose','')} |  |")
    return "\n".join(rows)

def build_inventory(mods: List[Dict]) -> str:
    parts: List[str] = []
    for m in mods:
        pid, pth, role = m.get("id"), m.get("path"), m.get("purpose","")
        p = ROOT / (pth or "")
        files = list_key_files(p)
        rel_files = []
        for f in files:
            try:
                rel = f.relative_to(ROOT)
            except ValueError:
                rel = f
            rel_files.append(rel.as_posix())
        file_lines = [f"  - `{item}`" for item in rel_files] or ["  - _(none found)_"]
        sig_lines: List[str] = []
        for f in files[:4]:
            sigs = sigs_from_file(f)
            if sigs:
                sig_lines.append(f"  - **{f.name}**: " + "; ".join(sigs))
        if not sig_lines:
            sig_lines = ["  - _(no public signatures detected)_"]
        block_lines = [
            f"### {pid}",
            f"- **Path**: `{pth}`",
            f"- **Purpose**: {role}",
            "- **Key files**",
            *file_lines,
            "- **Public interfaces (signatures)**",
            *sig_lines,
        ]
        parts.append("\n".join(block_lines))
    return "\n\n".join(parts)

def replace_block(text: str, begin: str, end: str, content: str) -> str:
    import re
    pat = re.compile(rf"({re.escape(begin)})(.*?)(\s*{re.escape(end)})", re.DOTALL)
    repl = f"{begin}\n{content}\n{end}"
    return pat.sub(repl, text, count=1) if pat.search(text) else f"{text.rstrip()}\n\n{repl}\n"

def main():
    m = load_manifest()
    mods = [x for x in (m.get("modules") or []) if x.get("path") and (ROOT / x["path"]).exists()]
    repo_map = build_repo_map(mods)
    inventory = build_inventory(mods)
    md = SPEC_MD.read_text("utf-8")
    md = replace_block(md, "<!-- REPO_MAP:BEGIN -->", "<!-- REPO_MAP:END -->", repo_map)
    md = replace_block(md, "<!-- MODULE_INVENTORY:BEGIN -->", "<!-- MODULE_INVENTORY:END -->", inventory)
    SPEC_MD.write_text(md, encoding="utf-8")
    print("[spec_sweeper] updated", SPEC_MD)

if __name__ == "__main__":
    main()
