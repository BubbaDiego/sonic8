from __future__ import annotations
import os, sys, importlib, traceback
from pathlib import Path
from typing import List, Tuple

def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here, *here.parents]:
        if (p / "backend").exists():
            return p
    # fallback: <repo>/backend/console/.. -> repo
    return here.parents[2]

def _try_candidates(candidates: List[Tuple[str, str]]) -> int:
    errors = []
    for mod_name, attr in candidates:
        try:
            mod = importlib.import_module(mod_name)
            fn = getattr(mod, attr, None)
            if callable(fn):
                print(f"[cyclone] using {mod_name}:{attr}")
                rv = fn()
                return int(rv) if isinstance(rv, int) else 0
            else:
                errors.append(f"{mod_name}:{attr} (no callable)")
        except Exception as e:
            errors.append(f"{mod_name}:{attr} -> {e.__class__.__name__}: {e}")
    print("[cyclone] No usable entry found. Tried:")
    for line in errors:
        print(f"  - {line}")
    return 2

def main() -> int:
    root = _repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.environ["PYTHONPATH"] = str(root) + os.pathsep + os.environ.get("PYTHONPATH", "")

    # Try the most probable Cyclone entrypoints in sonic7.
    candidates: List[Tuple[str, str]] = [
        ("backend.core.cyclone_core.cyclone_console", "main"),
        ("backend.core.cyclone_core.cyclone_console", "run"),
        ("backend.core.cyclone_core.cyclone_app", "main"),
        ("backend.core.cyclone_core.console", "main"),
        ("backend.core.cyclone_core.app", "main"),
        # legacy/alt fallbacks:
        ("backend.core.monitor_core.cyclone_console_service", "main"),
        ("backend.core.monitor_core.cyclone_console", "main"),
    ]
    return _try_candidates(candidates)

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        input("\n⏸  Press ENTER to exit…")
        sys.exit(1)

