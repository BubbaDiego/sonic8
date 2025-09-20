from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANON = ROOT / "backend" / "scripts" / "spec_validate.py"


if __name__ == "__main__":
    code = compile(CANON.read_text(encoding="utf-8"), str(CANON), "exec")
    glb = {"__name__": "__main__", "__file__": str(CANON)}
    try:
        exec(code, glb, glb)
    except SystemExit as e:
        sys.exit(e.code)
