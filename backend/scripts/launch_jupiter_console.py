"""Helper launcher for the Jupiter console."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    """Return the repository root assuming this file sits in ``backend/scripts``."""

    return Path(__file__).resolve().parents[2]


def launch(new_window: bool = True) -> None:
    args = [sys.executable, "-m", "backend.core.jupiter_core.console"]
    cwd = str(repo_root())
    title = "Jupiter Core Console"

    try:
        from backend.launch.utils import run_in_console  # type: ignore

        run_in_console(args, cwd=cwd, title=title, new_window=new_window)
        return
    except Exception:  # pragma: no cover - optional helper may not exist
        pass

    if os.name == "nt" and new_window:
        subprocess.Popen(["start", "cmd", "/k"] + args, cwd=cwd, shell=True)
    else:
        subprocess.Popen(args, cwd=cwd)


__all__ = ["launch", "repo_root"]
