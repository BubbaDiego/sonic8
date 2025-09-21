# coding: utf-8

"""Perps CLI Bridge debug harness."""

import json
import os
import runpy
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

# ── formatting helpers ────────────────────────────────────────────────────────

OK = "✅"
BAD = "❌"
INFO = "ℹ️ "
BOX = "─" * 70


def run(cmd, cwd=None):
    try:
        p = subprocess.run(
            cmd,
            cwd=cwd,
            shell=False,
            capture_output=True,
            text=True,
        )
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except FileNotFoundError as e:
        return 127, "", str(e)


def which(name):
    p = shutil.which(name)
    return p or ""


def pp(k, v, ok=True):
    mark = OK if ok else BAD
    print(f" {mark} {k:<24} {v}")


def kv(k, v):
    print(f" • {k:<24} {v}")


def header(title):
    print(f"\n{BOX}\n{title}\n{BOX}")


# ── project paths ─────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TEST_SCRIPT = SCRIPTS / "test_perps_cli_bridge.py"

# Optional TS repo (read-only; just to confirm presence)

DEFAULT_TS_REPO = r"C:\sonic5\jupiter-perps-anchor-idl-parsing"
TS_REPO = Path(os.environ.get("JUP_PERPS_TS_REPO", DEFAULT_TS_REPO))

# ── section: environment summary ──────────────────────────────────────────────

header("Perps CLI Bridge · Debug harness")

kv("Python", sys.version.split()[0])
kv("Python exe", sys.executable)
kv("Working dir", str(ROOT))
kv("Scripts dir", str(SCRIPTS))
kv("Test script", str(TEST_SCRIPT))
kv("TS repo (optional)", str(TS_REPO))

# ── section: tool presence ───────────────────────────────────────────────────

header("Toolchain checks")

node = which("node")
npx = which("npx")
pp("node.exe", node or "NOT FOUND", ok=bool(node))
pp("npx.exe", npx or "NOT FOUND", ok=bool(npx))

rc, out, err = run(["node", "-v"]) if node else (127, "", "")
pp("node -v", out or (err or "NOT RUN"), ok=(rc == 0))

rc, out, err = run(["npm", "-v"])
pp("npm -v", out or (err or "NOT RUN"), ok=(rc == 0))

# Try ts-node via npx without installing globally (no prompts with -y)

tsnode_ok = False
if npx:
    rc, out, err = run(["npx", "-y", "ts-node", "--version"])
    tsnode_ok = rc == 0
    pp("ts-node --version", out or (err or "NOT RUN"), ok=tsnode_ok)
else:
    pp("ts-node --version", "npx missing", ok=False)

# ── section: repo file presence (informational; no changes) ──────────────────

header("Repository probes (informational)")
if TS_REPO.exists():
    pp("TS repo path", str(TS_REPO), ok=True)
    # spot-check a couple files that often exist in that repo
    probes = [
        TS_REPO / "remaining-accounts.ts",
        TS_REPO / "jupiter-perpetuals-idl.ts",
        TS_REPO / "create-market-trade-request.ts",
    ]
    for p in probes:
        pp(f"exists: {p.name}", "yes" if p.exists() else "no", ok=p.exists())
else:
    pp("TS repo path", "MISSING (ok if unused for this test)", ok=False)

# ── section: run the Python bridge self-test script (no pytest) ───────────────

header("Execute test_perps_cli_bridge.py (script mode)")

if not TEST_SCRIPT.exists():
    print(f" {BAD} test script not found at: {TEST_SCRIPT}")
    sys.exit(2)

# Make sure backend is on sys.path for any intra-project imports

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Surface a few env vars but DO NOT modify your .env

kv("PERPS_BRIDGE_DEBUG", os.environ.get("PERPS_BRIDGE_DEBUG", "<unset>"))
kv("JUP_PERPS_TS_REPO", os.environ.get("JUP_PERPS_TS_REPO", "<unset>"))

print("\n " + INFO + "Running script with full trace…\n")

exit_code = 0
try:
    # Execute as if it were main (captures SystemExit cleanly)
    runpy.run_path(str(TEST_SCRIPT), run_name="main")
    pp("Script finished", "OK", ok=True)
except SystemExit as e:
    exit_code = int(e.code) if isinstance(e.code, int) else 1
    if exit_code == 0:
        pp("SystemExit", "exit code 0", ok=True)
    else:
        pp("SystemExit", f"exit code {exit_code}", ok=False)
except Exception:
    exit_code = 1
    print(f" {BAD} Uncaught exception while running test script:\n")
    traceback.print_exc()

header("Result")
if exit_code == 0:
    print(f" {OK} Bridge test: PASS")
else:
    print(f" {BAD} Bridge test: FAIL (exit={exit_code})")

sys.exit(exit_code)
