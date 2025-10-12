from __future__ import annotations

import importlib
import os
import sys
import traceback
from pathlib import Path
from typing import Callable, List, Optional, Tuple

_DEF_FUNCS: Tuple[str, ...] = ("main", "run", "run_console", "run_cyclone_console", "start")


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here, *here.parents]:
        if (p / "backend").exists():
            return p
    # fallback: <repo>/backend/console/.. -> repo
    return here.parents[2]


def _call_entry(mod_name: str, func: str) -> Optional[int]:
    mod = importlib.import_module(mod_name)
    fn: Optional[Callable[..., object]] = getattr(mod, func, None)
    if not callable(fn):
        raise AttributeError(f"{mod_name}:{func} (no callable)")
    rv = fn()
    return int(rv) if isinstance(rv, int) else 0


def _try_candidates(candidates: List[Tuple[str, str]]) -> Tuple[Optional[int], List[str]]:
    errors: List[str] = []
    for mod_name, func in candidates:
        try:
            return _call_entry(mod_name, func), errors
        except Exception as e:  # pragma: no cover - diagnostic output
            errors.append(f"{mod_name}:{func} -> {e.__class__.__name__}: {e}")
    return None, errors


def _discover_modules(root: Path) -> List[str]:
    """Find python modules under backend/ whose filename contains 'cyclone'."""

    backend = root / "backend"
    mods: List[str] = []
    for path in backend.rglob("*.py"):
        name = path.name.lower()
        if "__init__" in name or "test" in name:
            continue
        if "cyclone" not in name:
            continue
        try:
            rel = path.relative_to(root).with_suffix("")
            mod_name = ".".join(rel.parts)
        except Exception:
            continue
        mods.append(mod_name)

    # De-dup while preserving order
    seen: set[str] = set()
    out: List[str] = []
    for mod_name in mods:
        if mod_name in seen:
            continue
        seen.add(mod_name)
        out.append(mod_name)
    return out


def _try_discovery(root: Path) -> Tuple[Optional[int], List[str]]:
    errs: List[str] = []
    for mod_name in _discover_modules(root):
        for func in _DEF_FUNCS:
            try:
                return _call_entry(mod_name, func), errs
            except Exception as e:  # pragma: no cover - diagnostic output
                errs.append(f"{mod_name}:{func} -> {e.__class__.__name__}: {e}")
    return None, errs


def main() -> int:
    root = _repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.environ["PYTHONPATH"] = str(root) + os.pathsep + os.environ.get("PYTHONPATH", "")

    # 0) Explicit override
    override = os.environ.get("CYCLONE_ENTRY", "").strip()
    if override:
        mod_name, _, func = override.partition(":")
        func = func or "main"
        print(f"[cyclone] override: {mod_name}:{func}")
        try:
            return _call_entry(mod_name, func) or 0
        except Exception:  # pragma: no cover - diagnostic output
            traceback.print_exc()
            return 2

    # 1) Static candidates (fast)
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
    rv, tried = _try_candidates(candidates)
    if rv is not None:
        print(f"[cyclone] using candidates: exit={rv}")
        return rv

    # 2) Dynamic discovery across backend/
    drv, derrs = _try_discovery(root)
    if drv is not None:
        print(f"[cyclone] discovery hit: exit={drv}")
        return drv

    print("[cyclone] No usable entry found. Tried:")
    for line in [*tried, *derrs]:
        print(f"  - {line}")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        input("\n⏸  Press ENTER to exit…")
        sys.exit(1)

