from __future__ import annotations
import subprocess
import sys

CMDs = [
    [sys.executable, "backend/scripts/spec_validate.py"],
    [sys.executable, "backend/scripts/validate_ui_manifest.py"],
]

def main() -> int:
    failed = False
    for cmd in CMDs:
        print("\n=== RUN", " ".join(cmd), "===")
        rc = subprocess.call(cmd)
        if rc != 0:
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
