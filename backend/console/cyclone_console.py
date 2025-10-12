from __future__ import annotations

import ast
import os
import runpy
import sys
import traceback
from pathlib import Path
from typing import List, Optional, Tuple

_DEF_FUNCS: Tuple[str, ...] = ("main", "run", "run_console", "run_cyclone_console", "start")


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here, *here.parents]:
        if (p / "backend").exists():
            return p
    return here.parents[2]


def _is_console_dir(path: Path) -> bool:
    parts = [part.lower() for part in path.parts]
    return "backend" in parts and "console" in parts


def _candidate_files(root: Path) -> List[Path]:
    """Prefer obvious console-like files; fallback to any cyclone file (excluding our console dir)."""

    backend = root / "backend"
    if not backend.exists():
        return []

    picks: List[Path] = []

    def add_path(path: Path) -> None:
        if _is_console_dir(path.parent):
            return
        if path in picks:
            return
        picks.append(path)

    priority = (
        "cyclone_console.py",
        "cyclone_app.py",
        "cyclone_cli.py",
        "console_cyclone.py",
    )

    for path in backend.rglob("*.py"):
        if path.name.lower() in priority:
            add_path(path)

    for path in backend.rglob("*.py"):
        name = path.name.lower()
        if "cyclone" in name and ("console" in name or "cli" in name):
            add_path(path)

    for path in backend.rglob("*.py"):
        if "cyclone" in path.name.lower():
            add_path(path)

    return picks


def _functions_in_file(py_file: Path) -> List[str]:
    try:
        src = py_file.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(src, filename=str(py_file))
    except Exception:
        return []

    names: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in _DEF_FUNCS:
            names.append(node.name)

    seen: set[str] = set()
    ordered: List[str] = []
    for fn in _DEF_FUNCS:
        if fn in names and fn not in seen:
            ordered.append(fn)
            seen.add(fn)
    return ordered


def _run_file_func(py_file: Path, func_name: str) -> Optional[int]:
    namespace = runpy.run_path(str(py_file), run_name="__main__")
    fn = namespace.get(func_name)
    if not callable(fn):
        raise AttributeError(f"{py_file}:{func_name} (no callable)")
    rv = fn()
    return int(rv) if isinstance(rv, int) else 0


def main() -> int:
    root = _repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.environ["PYTHONPATH"] = str(root) + os.pathsep + os.environ.get("PYTHONPATH", "")

    override = os.environ.get("CYCLONE_ENTRY", "").strip()
    if override:
        mod, _, func = override.partition(":")
        func = func or "main"
        print(f"[cyclone] override (module): {mod}:{func}")
        try:
            module = __import__(mod, fromlist=["*"])
            target = getattr(module, func, None)
            if not callable(target):
                raise AttributeError(f"{mod}:{func} not callable")
            rv = target()
            return int(rv) if isinstance(rv, int) else 0
        except Exception:
            traceback.print_exc()
            return 2

    override_file = os.environ.get("CYCLONE_ENTRY_FILE", "").strip()
    if override_file:
        path_str, _, func = override_file.partition(":")
        func = func or "main"
        path = Path(path_str)
        py_file = path if path.is_absolute() else (root / path).resolve()
        print(f"[cyclone] override (file): {py_file}:{func}")
        try:
            return _run_file_func(py_file, func) or 0
        except Exception:
            traceback.print_exc()
            return 2

    errors: List[str] = []
    files = _candidate_files(root)
    tried_count = 0

    for py_file in files:
        funcs = _functions_in_file(py_file)
        if not funcs:
            continue
        for func in funcs:
            tried_count += 1
            try:
                print(f"[cyclone] trying {py_file.relative_to(root)}:{func}")
                rv = _run_file_func(py_file, func)
                print(f"[cyclone] launch ok: exit={rv}")
                return rv
            except Exception as exc:  # pragma: no cover - diagnostic output
                errors.append(
                    f"{py_file.relative_to(root)}:{func} -> {exc.__class__.__name__}: {exc}"
                )

    print("[cyclone] No usable entry found.")
    if tried_count:
        print("Tried (file:function):")
        for line in errors[:200]:
            print(f"  - {line}")
        if len(errors) > 200:
            print(f"  … and {len(errors) - 200} more")
    else:
        print("No files with suitable functions were found under backend/.")
        print(
            "Hint: set CYCLONE_ENTRY='module.path:main' or "
            "CYCLONE_ENTRY_FILE='backend/…/file.py:main'"
        )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        input("\n⏸ Press ENTER to exit…")
        sys.exit(1)
