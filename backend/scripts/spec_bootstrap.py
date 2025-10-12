from __future__ import annotations

import os
import subprocess
import sys
from importlib import import_module
from pathlib import Path
from typing import List, Tuple

# Map pip package → python module to import
REQUIRED = [("pyyaml", "yaml"), ("jsonschema", "jsonschema")]  # minimal toolchain for spec/UI


def _pip_install(pkg: str) -> None:
    """Install a package into the current venv using the same interpreter."""
    # Use OS-backed stdio to avoid fileno() complaints from wrapped streams
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", pkg],
            stdout=sys.__stdout__,
            stderr=sys.__stderr__,
        )
    except Exception:
        # Fallback: inherit parent's stdio
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])


def ensure_repo_root_and_path() -> Path:
    """
    Find the repo root (directory that contains 'backend') relative to this file,
    chdir into it, and add it to sys.path for in-process imports. Also inject into
    PYTHONPATH so child processes launched by the runner see the same path.
    """
    here = Path(__file__).resolve()

    # If we live under <repo>/backend/scripts/, repo root is 2 levels up.
    if here.parent.name == "scripts" and here.parent.parent.name == "backend":
        root = here.parents[2]
    else:
        # Otherwise find a directory where 'backend' is an immediate child.
        root = None
        for p in [here, *here.parents]:
            if (p / "backend").is_dir() and not (p / "backend" / "backend").exists():
                root = p
                break
        if root is None:
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
    missing: List[Tuple[str, str]] = []

    def _try_import(name: str) -> bool:
        try:
            import_module(name)
            return True
        except Exception:
            return False

    for pkg, mod in REQUIRED:
        if _try_import(mod):
            available.append(mod)
        else:
            missing.append((pkg, mod))

    if missing and install:
        for pkg, _ in list(missing):
            _pip_install(pkg)
        # verify again
        still_missing: List[Tuple[str, str]] = []
        for pkg, mod in list(missing):
            if _try_import(mod):
                available.append(mod)
            else:
                still_missing.append((pkg, mod))
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
    print(f"[spec-bootstrap] available={avail} missing={[m[1] for m in miss]}")
    if miss:
        # We do not hard-exit; we leave it to callers to decide. But we print loudly.
        print("[spec-bootstrap] WARNING: some packages are still missing; downstream steps may fail.")


if __name__ == "__main__":
    preflight(install=True)
