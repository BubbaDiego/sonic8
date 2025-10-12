from __future__ import annotations

import ast
import os
import runpy
import sys
import traceback
from pathlib import Path
from typing import List, Optional

_DEF_FUNCS = ("main", "run", "run_console", "run_cyclone_console", "start")
_BANNER_HINTS = (
    "Cyclone Interactive Console",
    "=== Cyclone",
    "Cyclone App",
    "Cyclone Console",
)


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here, *here.parents]:
        if (p / "backend").exists():
            return p
    return here.parents[2]


def _is_console_pkg(p: Path) -> bool:
    parts = [x.lower() for x in p.parts]
    return "backend" in parts and "console" in parts


def _candidate_files(root: Path) -> List[Path]:
    backend = root / "backend"
    if not backend.exists():
        return []
    picks: List[Path] = []

    # 1) Obvious names
    priority = ("cyclone_console.py", "cyclone_app.py", "cyclone_cli.py", "console_cyclone.py")
    for path in backend.rglob("*.py"):
        if _is_console_pkg(path.parent):
            continue
        name = path.name.lower()
        if name in priority:
            picks.append(path)

    # 2) any *cyclone* with *console|cli* in name
    for path in backend.rglob("*.py"):
        if _is_console_pkg(path.parent):
            continue
        name = path.name.lower()
        if "cyclone" in name and ("console" in name or "cli" in name) and path not in picks:
            picks.append(path)

    # 3) any *cyclone*.py outside console pkg
    for path in backend.rglob("*.py"):
        if _is_console_pkg(path.parent):
            continue
        if "cyclone" in path.name.lower() and path not in picks:
            picks.append(path)

    return picks


def _functions_in_file(py_file: Path) -> List[str]:
    try:
        src = py_file.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(src, filename=str(py_file))
    except Exception:
        return []
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in _DEF_FUNCS:
            names.append(node.name)
    # Preserve our priority order
    out = [fn for fn in _DEF_FUNCS if fn in names]
    return out


def _has_main_guard_or_banner(py_file: Path) -> bool:
    try:
        src = py_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    if "__name__" in src and "__main__" in src:
        return True
    ls = src.lower()
    return any(h.lower() in ls for h in _BANNER_HINTS)


def _run_file_func(py_file: Path, func_name: str) -> Optional[int]:
    ns = runpy.run_path(str(py_file), run_name="__main__")
    fn = ns.get(func_name)
    if not callable(fn):
        raise AttributeError(f"{py_file}:{func_name} (no callable)")
    rv = fn()
    return int(rv) if isinstance(rv, int) else 0


def _run_file_main_guard(py_file: Path) -> Optional[int]:
    # Executes a script-style console that uses a main guard or prints a Cyclone banner.
    runpy.run_path(str(py_file), run_name="__main__")
    return 0


def main() -> int:
    root = _repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.environ["PYTHONPATH"] = str(root) + os.pathsep + os.environ.get("PYTHONPATH", "")

    override = os.environ.get("CYCLONE_ENTRY", "").strip()
    if override:
        mod, _, fn = override.partition(":")
        fn = fn or "main"
        print(f"[cyclone] override (module): {mod}:{fn}")
        try:
            module = __import__(mod, fromlist=["*"])
            target = getattr(module, fn, None)
            if not callable(target):
                raise AttributeError(f"{mod}:{fn} not callable")
            rv = target()
            return int(rv) if isinstance(rv, int) else 0
        except Exception:
            traceback.print_exc()
            return 2

    override_file = os.environ.get("CYCLONE_ENTRY_FILE", "").strip()
    if override_file:
        path_str, _, fn = override_file.partition(":")
        fn = fn or "main"
        path = Path(path_str)
        py_file = path if path.is_absolute() else (root / path).resolve()
        print(f"[cyclone] override (file): {py_file}:{fn}")
        try:
            # If a function was specified, try that; else run main guard.
            if fn:
                try:
                    return _run_file_func(py_file, fn) or 0
                except Exception:
                    # fall back to main-guard
                    return _run_file_main_guard(py_file) or 0
            return _run_file_main_guard(py_file) or 0
        except Exception:
            traceback.print_exc()
            return 2

    errors: List[str] = []
    tried_any = False
    for py_file in _candidate_files(root):
        funcs = _functions_in_file(py_file)
        for func in funcs:
            tried_any = True
            try:
                print(f"[cyclone] trying {py_file.relative_to(root)}:{func}")
                rv = _run_file_func(py_file, func)
                print(f"[cyclone] launch ok: exit={rv}")
                return rv
            except Exception as exc:  # pragma: no cover - diagnostic output
                errors.append(
                    f"{py_file.relative_to(root)}:{func} -> {exc.__class__.__name__}: {exc}"
                )

    # 2) Script-style fallback: run files that look like consoles by main guard/banner (no function required)
    scripts = [p for p in _candidate_files(root) if _has_main_guard_or_banner(p)]
    for py_file in scripts:
        tried_any = True
        try:
            print(
                f"[cyclone] running script {py_file.relative_to(root)} (main-guard/banner)"
            )
            rv = _run_file_main_guard(py_file)
            print(f"[cyclone] launch ok: exit={rv}")
            return rv
        except Exception as exc:
            errors.append(
                f"{py_file.relative_to(root)}:__main__ -> {exc.__class__.__name__}: {exc}"
            )

    print("[cyclone] No usable entry found.")
    if tried_any and errors:
        print("Tried:")
        for line in errors[:200]:
            print(f"  - {line}")
        if len(errors) > 200:
            print(f"  … and {len(errors) - 200} more")
    else:
        print("No files that look like a Cyclone console were found under backend/.")
        print(
            "Hint: set CYCLONE_ENTRY='module.path:main' or "
            "CYCLONE_ENTRY_FILE='backend/…/file.py[:main]'"
        )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        input("\n⏸ Press ENTER to exit…")
        sys.exit(1)
