from __future__ import annotations

import os
import subprocess
import sys
from importlib import import_module
from pathlib import Path
from typing import List, Tuple

REQUIRED_PACKAGES = ["pyyaml", "jsonschema"]  # minimal toolchain for spec & UI sweeper


def _pip_install(pkg: str) -> None:
    """Install a package into the current venv using the same interpreter."""
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", pkg],
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


def ensure_repo_root_and_path() -> Path:
    """
    Find the repo root (directory that contains 'backend') relative to this file,
    chdir into it, and add it to sys.path for in-process imports. Also inject into
    PYTHONPATH so child processes launched by the runner see the same path.
    """
    here = Path(__file__).resolve()

    # walk up until we find a folder containing backend/
    root: Path | None = None
    for p in here.parents:
        if (p / "backend").exists():
            root = p
            break

    if root is None:
        # fallback: two levels up is typical: <repo>/backend/scripts/spec_bootstrap.py
        root = here.parents[2]

    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    # propagate to child processes
    prev = os.environ.get("PYTHONPATH", "")
    parts = [x for x in prev.split(os.pathsep) if x]
    if str(root) not in parts:
        os.environ["PYTHONPATH"] = str(root) + (os.pathsep + prev if prev else "")

    return root


def ensure_spec_toolchain(install: bool = True) -> Tuple[List[str], List[str]]:
    """
    Ensure the spec toolchain is importable. Returns (available, missing).
    If install=True, missing packages are installed and re-checked.
    """
    available: List[str] = []
    missing: List[str] = []

    def _try_import(name: str) -> bool:
        try:
            import_module(name)
            return True
        except Exception:
            return False

    for name in REQUIRED_PACKAGES:
        if _try_import(name):
            available.append(name)
        else:
            missing.append(name)

    if missing and install:
        for pkg in list(missing):
            _pip_install(pkg)
        # verify again
        still_missing = []
        for name in list(missing):
            if _try_import(name):
                available.append(name)
            else:
                still_missing.append(name)
        missing = still_missing

    return available, missing


def preflight(install: bool = True) -> None:
    """
    One-call preflight for the maintenance runner.
    - locks cwd to repo root
    - ensures pythonpath for subprocess children
    - ensures spec toolchain (pyyaml/jsonschema)
    """
    root = ensure_repo_root_and_path()
    avail, miss = ensure_spec_toolchain(install=install)
    print(f"[spec-bootstrap] repo_root={root}")
    print(f"[spec-bootstrap] available={avail} missing={miss}")
    if miss:
        # We do not hard-exit; we leave it to callers to decide. But we print loudly.
        print("[spec-bootstrap] WARNING: some packages are still missing; downstream steps may fail.")


if __name__ == "__main__":
    preflight(install=True)
