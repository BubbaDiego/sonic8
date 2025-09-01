# update_spec.py  (place anywhere inside the repo or bundle)
from __future__ import annotations
import argparse, os, sys, subprocess
from pathlib import Path
from typing import List

# Heuristic: walk up until we find a folder that looks like the repo root
def find_repo_root(start: Path) -> Path:
    cur = start
    for _ in range(6):  # go up max 6 levels
        if (cur / "api").is_dir() and (cur / "docs").is_dir():
            return cur
        cur = cur.parent
    return start  # fallback

def run_step(cmd: List[str], title: str, cwd: Path, halt: bool) -> int:
    print(f"\n=== {title} ===")
    print(f"> {' '.join(cmd)}  (cwd={cwd})")
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), check=False)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return 1
    if proc.returncode == 0:
        print(f"[OK] {title}")
    else:
        print(f"[FAIL] {title} (exit={proc.returncode})")
        if "generate_openapi.py" in " ".join(cmd):
            print("  Tip: pip install pyyaml")
            print("  Tip: ensure api/generate_openapi.py imports your FastAPI `app`.")
        if halt:
            sys.exit(proc.returncode)
    return proc.returncode

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["openapi  ", "sync", "validate"])
    parser.add_argument("--skip-openapi", action="store_true")
    parser.add_argument("--skip-sync", action="store_true")
    parser.add_argument("--skip-validate", action="store_true")
    parser.add_argument("--no-raise", action="store_true")
    args = parser.parse_args()

    start = Path(__file__).resolve().parent
    ROOT = find_repo_root(start)
    print(f"Repo root: {ROOT}")

    steps = []
    if args.only == "openapi":
        steps = [("Generate OpenAPI", [sys.executable, "api/generate_openapi.py"])]
    elif args.only == "sync":
        steps = [("Spec Sync", [sys.executable, "scripts/spec_sync.py"])]
    elif args.only == "validate":
        steps = [("Spec Validate", [sys.executable, "scripts/spec_validate.py"])]
    else:
        if not args.skip_openapi:
            steps.append(("Generate OpenAPI", [sys.executable, "api/generate_openapi.py"]))
        if not args.skip_sync:
            steps.append(("Spec Sync", [sys.executable, "scripts/spec_sync.py"]))
        if not args.skip_validate:
            steps.append(("Spec Validate", [sys.executable, "scripts/spec_validate.py"]))

    if not steps:
        print("Nothing to do.")
        return 0

    rc = 0
    for title, cmd in steps:
        rc = run_step(cmd, title, cwd=ROOT, halt=not args.no_raise) or rc

    print("\n=== Done ===")
    print("All steps completed." if rc == 0 else "One or more steps failed.")
    return rc

if __name__ == "__main__":
    raise SystemExit(main())
