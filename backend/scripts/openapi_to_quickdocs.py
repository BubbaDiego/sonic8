#!/usr/bin/env python3
r"""
Generate Markdown API docs from OpenAPI, auto-detecting repo root.

Outputs:
  - docs/spec/api_index.md
  - docs/teaching_pack/04_api_quick.md

CLI (optional):
  --in <path>         # defaults to api/openapi.yaml under detected root
  --spec-out <path>   # defaults to docs/spec/api_index.md under root
  --quick-out <path>  # defaults to docs/teaching_pack/04_api_quick.md under root
"""
from __future__ import annotations
import argparse, textwrap
from pathlib import Path
import yaml

METHODS = ["get","post","put","patch","delete","options","head"]

def find_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(7):
        if (cur / "api" / "openapi.yaml").exists():
            return cur
        cur = cur.parent
    # fallback: if user set SONIC_ROOT
    env = Path.home()  # dummy fallback to avoid crashing
    return start.resolve().parents[2]

def schema_label(s):
    if not s: return ""
    if "$ref" in s:
        return s["$ref"].split("/")[-1]
    t = s.get("type")
    if t == "array":
        return f"array[{schema_label(s.get('items'))}]"
    if t: return t
    return ""

def param_line(p):
    name = p.get("name","?")
    loc = p.get("in","?")
    req = "required" if p.get("required") else "optional"
    typ = schema_label((p.get("schema") or {}))
    desc = (p.get("description") or "").strip().replace("\n"," ")
    return f"- `{name}` ({loc}, {req}): {typ}{' — '+desc if desc else ''}"

def body_line(rb):
    if not rb: return "—"
    ct = list((rb.get("content") or {}).keys())
    media = ct[0] if ct else "application/json"
    sch = (rb.get("content") or {}).get(media,{}).get("schema",{})
    return f"{media} → {schema_label(sch)}"

def response_line(code, r):
    desc = (r.get("description") or "").strip().replace("\n"," ")
    return f"- **{code}**: {desc or '—'}"

def gen_api_index(spec: dict) -> str:
    info = spec.get("info",{})
    servers = [s.get("url") for s in spec.get("servers",[])] or []
    out = [f"# API Index — {info.get('title','Sonic API')}\n"]
    if servers:
        out.append("**Servers:** " + ", ".join(servers) + "\n")
    paths = spec.get("paths",{}) or {}
    for path in sorted(paths.keys()):
        out.append(f"## `{path}`\n")
        item = paths[path] or {}
        for m in METHODS:
            if m in item:
                op = item[m] or {}
                summ = op.get("summary") or op.get("operationId") or ""
                out.append(f"### {m.upper()} {path}")
                if summ: out.append(f"*{summ}*")
                params = (item.get("parameters") or []) + (op.get("parameters") or [])
                if params:
                    out.append("\n**Parameters**")
                    for p in params: out.append(param_line(p))
                if "requestBody" in op:
                    out.append("\n**Request Body**")
                    out.append("- " + body_line(op["requestBody"]))
                resps = op.get("responses",{}) or {}
                if resps:
                    out.append("\n**Responses**")
                    for code, r in resps.items():
                        out.append(response_line(code, r or {}))
                out.append("")
    return "\n".join(out).strip() + "\n"

def gen_quick(spec: dict) -> str:
    info = spec.get("info",{})
    base = (spec.get("servers") or [{}])[0].get("url","http://localhost:8000")
    lines = [
        "# API Quick Reference\n",
        f"**Auth:** `Authorization: Bearer <token>`  ",
        f"**Base URL (dev):** `{base}`\n",
        "## Endpoints\n",
    ]
    for path, item in sorted((spec.get("paths",{}) or {}).items()):
        for m in METHODS:
            if m in (item or {}):
                op = item[m] or {}
                summ = op.get("summary") or op.get("operationId") or ""
                lines.append(f"- **{m.upper()} {path}** — {summ}".rstrip(" —"))
    lines.append("")
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=None)
    ap.add_argument("--spec-out", default=None)
    ap.add_argument("--quick-out", default=None)
    args = ap.parse_args()

    # auto-detect root (look upward for api/openapi.yaml)
    start = Path(__file__).resolve().parent
    ROOT = find_root(start)

    inp = Path(args.inp) if args.inp else ROOT / "api" / "openapi.yaml"
    spec_out = Path(args.spec_out) if args.spec_out else ROOT / "docs" / "spec" / "api_index.md"
    quick_out = Path(args.quick_out) if args.quick_out else ROOT / "docs" / "teaching_pack" / "04_api_quick.md"

    spec = yaml.safe_load(inp.read_text(encoding="utf-8"))
    spec_out.parent.mkdir(parents=True, exist_ok=True)
    quick_out.parent.mkdir(parents=True, exist_ok=True)

    spec_out.write_text(gen_api_index(spec), encoding="utf-8")
    quick_out.write_text(gen_quick(spec), encoding="utf-8")

    print(f"Repo root: {ROOT}")
    print(f"Wrote {spec_out}")
    print(f"Wrote {quick_out}")

if __name__ == "__main__":
    main()
