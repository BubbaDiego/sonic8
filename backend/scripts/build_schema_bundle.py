from __future__ import annotations

import argparse
import datetime as _dt
import json
from pathlib import Path
from typing import Dict, List, Any
import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "spec" / "spec.manifest.yaml"
SCHEMAS_DIR = ROOT / "docs" / "spec" / "schemas"
OUT_JSON = ROOT / "docs" / "spec" / "schema_bundle.json"
OUT_MD   = ROOT / "docs" / "spec" / "schema_book.md"

def _now_iso() -> str:
    return _dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

def load_manifest() -> Dict[str, Any]:
    if not MANIFEST.exists():
        raise SystemExit(f"missing manifest: {MANIFEST}")
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}

def index_schemas(m: Dict[str, Any]) -> Dict[str, Path]:
    idx: Dict[str, Path] = {}
    for s in (m.get("schemas") or []):
        sid, p = s.get("id"), s.get("path")
        if not sid or not p:
            continue
        sp = ROOT / p if not str(p).startswith(("http://","https://","/")) else Path(p)
        idx[sid] = sp
    return idx

def build_api_to_schema(m: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
    by_schema: Dict[str, List[Dict[str, str]]] = {}
    for a in (m.get("apis") or []):
        sid = a.get("response_schema")
        if not sid:
            continue
        by_schema.setdefault(sid, []).append({
            "method": (a.get("method") or "").upper(),
            "path": a.get("path") or "",
            "id": a.get("id") or ""
        })
    return by_schema

def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"$error": f"Failed to load {path.name}: {e}"}

def pick_subset(all_ids: List[str], include: List[str], include_prefix: List[str]) -> List[str]:
    if not include and not include_prefix:
        return all_ids
    chosen = set(include)
    for sid in all_ids:
        if any(sid.startswith(pref) for pref in include_prefix):
            chosen.add(sid)
    return [sid for sid in all_ids if sid in chosen]

def render_markdown(bundle: Dict[str, Any], api_map: Dict[str, List[Dict[str, str]]], meta: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append(f"# Sonic Schema Book — Teaching Bundle")
    lines.append("")
    lines.append(f"> Generated: {meta['generated_at']}  \n> Source: `docs/spec/spec.manifest.yaml`  \n> Note: This file consolidates many repo schemas into one for *teaching*. In the repository, each schema lives as its own JSON file.")
    lines.append("")
    lines.append("## API ⇄ Schema index")
    lines.append("")
    # Build API table
    rows = ["| Method | Path | Schema ID |", "|---|---|---|"]
    # invert map for table
    for sid, apis in sorted(api_map.items(), key=lambda x: x[0].lower()):
        for a in apis:
            rows.append(f"| `{a['method']}` | `{a['path']}` | `{sid}` |")
    if len(rows) == 2:
        rows.append("| — | — | — |")
    lines.extend(rows)
    lines.append("")
    lines.append("## Table of Contents")
    for sid in sorted(bundle.keys(), key=str.lower):
        lines.append(f"- [{sid}](#{sid.lower().replace('_','-')})")
    lines.append("")
    # Each schema with examples
    for sid in sorted(bundle.keys(), key=str.lower):
        s = bundle[sid]
        lines.append(f"---\n")
        lines.append(f"### {sid}")
        used = api_map.get(sid, [])
        if used:
            used_str = ", ".join(f"`{a['method']} {a['path']}`" for a in used)
            lines.append(f"**Used by:** {used_str}")
        else:
            lines.append(f"**Used by:** _not mapped_")
        # show examples if present
        ex = s.get("examples")
        if ex:
            lines.append("\n**Example**")
            # show first example only (keep file small)
            ex0 = ex[0]
            lines.append("```json")
            lines.append(json.dumps(ex0, indent=2, ensure_ascii=False))
            lines.append("```")
        # full schema
        lines.append("\n**Schema**")
        lines.append("```json")
        lines.append(json.dumps(s, indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--include", nargs="*", default=[], help="Exact schema ids to include (whitelist).")
    ap.add_argument("--include-prefix", nargs="*", default=[], help="Schema id prefixes to include (whitelist).")
    ap.add_argument("--output-json", default=str(OUT_JSON), help="Path to JSON bundle output.")
    ap.add_argument("--output-md", default=str(OUT_MD), help="Path to Markdown book output.")
    args = ap.parse_args()

    m = load_manifest()
    schema_idx = index_schemas(m)
    api_by_schema = build_api_to_schema(m)

    all_ids = list(schema_idx.keys())
    chosen_ids = pick_subset(all_ids, args.include, args.include_prefix)
    if not chosen_ids:
        raise SystemExit("No schemas selected (check --include / --include-prefix).")

    bundle: Dict[str, Any] = {}
    for sid in chosen_ids:
        p = schema_idx[sid]
        if p and p.exists():
            bundle[sid] = load_json(p)
        else:
            bundle[sid] = {"$error": f"Missing file for {sid}", "$path": str(p)}

    meta = {"generated_at": _now_iso(), "count": len(bundle)}
    # Write JSON bundle
    oj = Path(args.output_json)
    oj.parent.mkdir(parents=True, exist_ok=True)
    oj.write_text(json.dumps({
        "meta": meta,
        "schemas": bundle,
        "used_by_apis": api_by_schema
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[schema_bundle] wrote {oj}")

    # Write Markdown book
    om = Path(args.output_md)
    om.parent.mkdir(parents=True, exist_ok=True)
    om.write_text(render_markdown(bundle, api_by_schema, meta), encoding="utf-8")
    print(f"[schema_book] wrote {om}")

if __name__ == "__main__":
    main()
