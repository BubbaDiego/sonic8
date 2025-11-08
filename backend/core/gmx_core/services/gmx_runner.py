# Full file: thin wrapper to call the Rust runner and return JSON.
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

RUNNER_ROOT = Path(__file__).resolve().parents[1] / "rust"
CARGO_BIN = shutil.which("cargo") or "cargo"


class GmxRunnerError(RuntimeError):
    pass


def _run(args: list[str], cwd: Optional[Path] = None) -> Dict[str, Any]:
    proc = subprocess.run(
        args,
        cwd=str(cwd or RUNNER_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise GmxRunnerError(f"runner failed ({proc.returncode}):\n{proc.stderr or proc.stdout}")
    try:
        return json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError as e:
        raise GmxRunnerError(f"invalid JSON from runner: {e}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")


def health(cluster: str = "mainnet", signer: Optional[str] = None) -> Dict[str, Any]:
    args = [CARGO_BIN, "run", "--quiet", "--", "health", "--json", "--cluster", cluster]
    if signer:
        args += ["--signer", signer]
    return _run(args)


def markets(cluster: str = "mainnet", signer: Optional[str] = None) -> Dict[str, Any]:
    args = [CARGO_BIN, "run", "--quiet", "--", "markets", "--json", "--cluster", cluster]
    if signer:
        args += ["--signer", signer]
    return _run(args)


def positions(cluster: str = "mainnet", signer: Optional[str] = None) -> Dict[str, Any]:
    args = [CARGO_BIN, "run", "--quiet", "--", "positions", "--json", "--cluster", cluster]
    if signer:
        args += ["--signer", signer]
    return _run(args)
