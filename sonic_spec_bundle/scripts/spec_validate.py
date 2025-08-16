#!/usr/bin/env python3
"""
Basic spec validator for Sonic docs.
- Verifies that key files referenced by the master spec exist
- Fails non-zero on missing required anchors/files
"""
from __future__ import annotations
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    ROOT / "docs/spec/master.md",
    ROOT / "docs/spec/domain_glossary.md",
    ROOT / "docs/spec/architecture.md",
    ROOT / "docs/spec/codebase_map.md",
    ROOT / "docs/spec/workflows.md",
    ROOT / "docs/spec/conventions.md",
    ROOT / "docs/spec/ui_contracts.md",
    ROOT / "docs/spec/troubleshooting.md",
    ROOT / "docs/spec/non_goals.md",
    ROOT / "docs/teaching_pack/00_readme_first.md",
    ROOT / "docs/actions/sonic_actions.json",
]

def main():
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED if not p.exists()]
    if missing:
        print("Missing required spec files:\n- " + "\n- ".join(missing))
        sys.exit(1)
    print("Spec looks complete ✅")

if __name__ == "__main__":
    main()
