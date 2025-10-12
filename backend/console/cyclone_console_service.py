"""Support both module and script execution for the Cyclone console launcher."""

from __future__ import annotations

import sys
from pathlib import Path

# If we're executed as a plain script, __package__ is empty and relative imports fail.
if __package__ is None or __package__ == "":
    # Add repo root to sys.path so absolute import works
    here = Path(__file__).resolve()
    # repo root two levels up: .../backend/console/cyclone_console_service.py -> <repo>/
    repo_root = here.parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    # Try absolute import
    from backend.console.cyclone_console import main as _main  # type: ignore
else:
    # When run as a module, the relative import works fine
    from .cyclone_console import main as _main  # type: ignore

if __name__ == "__main__":
    raise SystemExit(_main())

