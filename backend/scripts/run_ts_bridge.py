# -- coding: utf-8 --
"""
Python runner that executes the TypeScript bridge shim via pnpm dlx tsx
and prints friendly logs.
"""

import json
import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

OK = "✅"
BAD = "❌"
INFO = "ℹ️ "
BOX = "─" * 70

def header(title: str) -> None:
    print(f"\n{BOX}\n{title}\n{BOX}")


def pp(label: str, value, ok: bool = True) -> None:
    print(f" {OK if ok else BAD} {label:<26} {value}")


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TS_REPO = ROOT.parent / "jupiter-perps-anchor-idl-parsing"
TS_REPO = Path(os.environ.get("JUP_PERPS_TS_REPO", str(DEFAULT_TS_REPO)))

header("TS Bridge Runner")
pp("Python", sys.version.split()[0])
pp("TS repo", str(TS_REPO), TS_REPO.exists())

# find pnpm
pnpm_path = shutil.which("pnpm")
pp("pnpm", pnpm_path or "NOT FOUND", bool(pnpm_path))

# quick pnpm -v
if pnpm_path:
    try:
        version = subprocess.check_output([pnpm_path, "-v"], text=True).strip()
        pp("pnpm -v", version, True)
    except Exception as exc:  # pragma: no cover - diagnostic path
        pp("pnpm -v", f"ERROR: {exc}", False)

# run the shim via pnpm dlx tsx
header("Executing: pnpm dlx tsx bridge/echo.ts")
cmd = [pnpm_path or "pnpm", "dlx", "tsx", "bridge/echo.ts"]
try:
    proc = subprocess.run(
        cmd,
        cwd=str(TS_REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    pp("exit code", proc.returncode, proc.returncode == 0)
    print(f"\n{INFO}stdout:")
    print((proc.stdout or "").strip() or "«empty»")
    if proc.returncode != 0:
        print(f"\n{BAD}stderr:")
        print((proc.stderr or "").strip() or "«empty»")
        sys.exit(proc.returncode)
except FileNotFoundError:
    print(
        f" {BAD} pnpm not found on PATH. Run corepack enable then corepack prepare pnpm@latest --activate."
    )
    sys.exit(127)
except Exception:  # pragma: no cover - diagnostic path
    traceback.print_exc()
    sys.exit(1)

# parse JSON and show a friendly line
try:
    data = json.loads(proc.stdout)
    header("Parsed payload")
    for key in ("ok", "emoji", "msg", "node", "cwd", "ts"):
        pp(key, data.get(key), True)
    print(f"\n{OK} TS bridge sanity-check passed.")
except Exception as exc:  # pragma: no cover - diagnostic path
    print(f"\n{BAD} Could not parse JSON from TS shim: {exc}")
    sys.exit(2)
