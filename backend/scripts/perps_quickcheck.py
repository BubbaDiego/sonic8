#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal runner for the TS Perps smoke tester, robust to Windows console encodings.
"""

import os, sys, subprocess, shlex, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]  # C:\sonic5
RUNNER = ROOT / "backend" / "scripts" / "perps_cli_smoke_test.py"

def sep(title: str):
    print("\n" + "─" * 20, title, "─" * 20)

def run(argv):
    cmd = [sys.executable, str(RUNNER), *argv]
    sep("CMD")
    print(" ", " ".join(shlex.quote(str(c)) for c in cmd))

    # Capture BYTES, then decode as UTF-8 w/ replacement to avoid cp1252 crashes
    p = subprocess.run(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,              # ← capture bytes
        shell=False,
        env=dict(os.environ),
    )
    out = (p.stdout or b"").decode("utf-8", errors="replace")
    err = (p.stderr or b"").decode("utf-8", errors="replace")

    if out.strip():
        sep("stdout")
        print(out)
    if err.strip():
        sep("stderr")
        print(err)

    sep(f"exit code = {p.returncode}")
    return p.returncode

if __name__ == "__main__":
    # Keep it safe unless you explicitly set JUP_PERPS_LIVE=1
    os.environ.setdefault("JUP_PERPS_LIVE", "0")

    # 1) Zero-arg path (SOL long, size=20, collat=12, dry-run)
    run([])

    # 2) Size-only (no collateral) to bypass WSOL wrapping
    run(["open", "--size-usd", "20", "--collat", "0"])

    # 3) Stable collateral (USDC) to avoid WSOL edge cases
    run([
        "open", "--size-usd", "20", "--collat", "12",
        "--collat-mint", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    ])
