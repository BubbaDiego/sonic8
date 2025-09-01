#!/usr/bin/env python3
"""
Spec Audit for Sonic — checks Codex's work, auto-detects repo root.

It looks upward for a folder that contains api/openapi.yaml and docs/spec,
then runs checks and writes docs/spec/_spec_audit_report.txt under that root.

Optional flags:
  --root C:\sonic5                 # force repo root
  --openapi api/openapi.yaml       # custom OpenAPI path relative to root
"""
from __future__ import annotations
from pathlib import Path
import re, sys, yaml, argparse

def find_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(8):
        if (cur / "api" / "openapi.yaml").exists() and (cur / "docs" / "spec").exists():
            return cur
        cur = cur.parent
    return start.resolve()

def get_ops(spec):
    for path, item in (spec.get("paths") or {}).items():
        for m in ("get","post","put","patch","delete","options","head"):
            if m in (item or {}):
                op = item[m] or {}
                yield path, m, item, op

def header_names(item, op):
    names = set()
    for p in (item.get("parameters") or []) + (op.get("parameters") or []):
        if str(p.get("in")).lower() == "header" and p.get("name"):
            names.add(p.get("name"))
    # normalize common header aliases
    return {n for n in names}

def has_auth(spec, item, op):
    if op.get("security") or spec.get("security"):
        return True
    # fallback: explicit header
    return any(h.lower() == "authorization" for h in header_names(item, op))

def _type_includes_string(prop: dict) -> bool:
    t = prop.get("type")
    if t == "string" or (isinstance(t, list) and "string" in t):
        return True
    for key in ("anyOf", "oneOf", "allOf"):
        alts = prop.get(key) or []
        if any(isinstance(a, dict) and (a.get("type") == "string" or ("type" in a and "string" in a["type"] if isinstance(a.get("type"), list) else False)) for a in alts):
            return True
    return False

def check_money_string(schema_obj):
    offenders = []
    props = (schema_obj or {}).get("properties", {}) or {}
    moneyish = {"price","qty","amount","collateral","entry_price","liquidation_price","leverage","balance","fee"}
    for k, v in props.items():
        if k in moneyish and not _type_includes_string(v):
            offenders.append((k, v.get("type")))
    return offenders


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=str, default=None)
    ap.add_argument("--openapi", type=str, default="api/openapi.yaml")
    args = ap.parse_args()

    start = Path(__file__).resolve().parent
    ROOT = Path(args.root).resolve() if args.root else find_root(start)
    OAS = ROOT / args.openapi
    REPORT = ROOT / "docs" / "spec" / "_spec_audit_report.txt"

    if not OAS.exists():
        print(f"openapi.yaml missing at {OAS.relative_to(ROOT)}")
        sys.exit(1)

    spec = yaml.safe_load(OAS.read_text(encoding="utf-8"))
    out = []

    def fail(msg): out.append(f"FAIL: {msg}")
    def warn(msg): out.append(f"warn: {msg}")
    def ok(msg):   out.append(f"ok:   {msg}")

    title = (spec.get("info") or {}).get("title","(no title)")
    ok(f"Loaded OpenAPI: {title}",)

    ops = list(get_ops(spec))
    paths_set = sorted({p for p,_,_,_ in ops})
    ok(f"Found {len(paths_set)} unique paths; {len(ops)} operations")

    writes = [(p,m,i,o) for p,m,i,o in ops if m in {"post","put","patch","delete"}]
    missing_auth, missing_idem = [], []
    for p,m,i,o in writes:
        if not has_auth(spec, i, o): missing_auth.append((m.upper(), p))
        if not any(h.lower()=="idempotency-key" for h in header_names(i, o)):
            missing_idem.append((m.upper(), p))

    if missing_auth: fail(f"{len(missing_auth)} write ops without auth: {missing_auth}")
    else: ok("All write ops have auth (security or Authorization header).")

    if missing_idem: warn(f"{len(missing_idem)} write ops missing Idempotency-Key header: {missing_idem}")
    else: ok("All write ops include Idempotency-Key header.")

    comps = (spec.get("components") or {}).get("schemas", {}) or {}
    offenders = {name: check_money_string(sch) for name, sch in comps.items()}
    offenders = {k:v for k,v in offenders.items() if v}
    if offenders:
        warn("Money-like fields not strings in components: " + ", ".join(f"{k}:{v}" for k,v in offenders.items()))
    else:
        ok("All money-like fields in components are strings (or nullable strings).")

    # Docs presence
    doc_gloss = ROOT/"docs/spec/domain_glossary.md"
    doc_wf = ROOT/"docs/spec/workflows.md"
    doc_ui = ROOT/"docs/spec/ui_contracts.md"
    doc_idx = ROOT/"docs/spec/api_index.md"
    doc_quick = ROOT/"docs/teaching_pack/04_api_quick.md"
    for p in [doc_gloss, doc_wf, doc_ui, doc_idx, doc_quick]:
        if not p.exists(): fail(f"Missing doc: {p.relative_to(ROOT)}")

    if doc_gloss.exists():
        gtxt = doc_gloss.read_text(encoding="utf-8")
        for term in ["Account","Position","Order","Signal","Strategy","Alert"]:
            if term not in gtxt: warn(f"Glossary missing term: {term}")
        else: ok("Glossary contains core terms.")

    if doc_wf.exists():
        w = doc_wf.read_text(encoding="utf-8").lower()
        for s in ["create order","adjust collateral","tp/sl","liquidation"]:
            if s not in w: warn(f"Workflows missing section: '{s}'")
        if "invariants" not in w: warn("Workflows missing 'Invariants'")
        if "failure mode" not in w: warn("Workflows missing 'Failure Modes'")
        if "```http" in w or "```python" in w: ok("Workflows include runnable example block.")

    if doc_idx.exists():
        idx = doc_idx.read_text(encoding="utf-8")
        miss = [p for p in paths_set if f"`{p}`" not in idx]
        if miss: fail(f"api_index.md missing paths: {miss}")
        else: ok("api_index.md includes all paths.")

    if doc_quick.exists():
        q = doc_quick.read_text(encoding="utf-8")
        miss = [(m.upper(), p) for p,m,_,_ in ops if f"- **{m.upper()} {p}**" not in q]
        if miss: warn(f"quick ref missing some ops: {miss}")
        else: ok("Quick ref includes all operations.")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(REPORT.relative_to(ROOT))
    sys.exit(1 if any(line.startswith("FAIL") for line in out) else 0)

if __name__ == "__main__":
    main()
