"""Interactive menu for the Topic Test Runner."""
from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Iterable, List

try:  # pragma: no cover
    import yaml
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

# Local, self-contained file matcher so the UI works even if topic_console wasn't updated yet
DEFAULT_ROOTS = [Path("test_core/tests"), Path("tests")]
API_HINTS = {"api", "fastapi", "openapi", "route", "routes", "bp", "blueprint"}
HEAVY_MARKERS = (
    "import fastapi",
    "from fastapi",
    "import starlette",
    "from starlette",
    "import pydantic",
    "from pydantic",
)

RECENTS_PATH = Path("test_core/reports/_recent_topics.json")
TOPICS_YAML = Path("test_core/topics.yaml")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _iter_test_files(roots: Iterable[Path] | None = None) -> list[Path]:
    roots = list(roots or DEFAULT_ROOTS)
    out: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root.is_file() and root.suffix == ".py":
            if root not in seen:
                out.append(root)
                seen.add(root)
        elif root.is_dir():
            for path in list(root.rglob("test_*.py")) + list(root.rglob("*_test.py")):
                if path not in seen:
                    out.append(path)
                    seen.add(path)
    return out


def _has_import_of(text_lower: str, needle: str) -> bool:
    for line in text_lower.splitlines():
        stripped = line.strip()
        if stripped.startswith("from ") or stripped.startswith("import "):
            if needle in stripped:
                return True
    return False


def _match_files_by_topic(topic: str) -> list[str]:
    query = topic.strip()
    if not query:
        return []
    terms = [word for word in (part.strip() for part in query.split()) if word]
    if not terms:
        return []

    terms_lower = [word.lower() for word in terms]
    include_api = any(word in API_HINTS for word in terms_lower)
    has_xcom = any(word == "xcom" for word in terms_lower)

    picks: list[str] = []
    for file_path in _iter_test_files():
        name_lower = file_path.name.lower()
        path_lower = str(file_path).lower()
        text_lower: str | None = None

        if not include_api:
            if text_lower is None:
                text_lower = _read_text(file_path).lower()
            if any(marker in text_lower for marker in HEAVY_MARKERS):
                continue

        matched = False
        if any(term in name_lower for term in terms_lower) or any(
            term in path_lower for term in terms_lower
        ):
            matched = True

        if not matched and has_xcom:
            if text_lower is None:
                text_lower = _read_text(file_path).lower()
            if (
                _has_import_of(text_lower, "xcom")
                or "xcom_" in text_lower
                or "xcom." in text_lower
            ):
                matched = True

        if not matched:
            for term in terms_lower:
                if len(term) <= 4 and not has_xcom:
                    if text_lower is None:
                        text_lower = _read_text(file_path).lower()
                    if (
                        f"{term}_" in text_lower
                        or f"{term}." in text_lower
                        or _has_import_of(text_lower, term)
                    ):
                        matched = True
                        break

        if matched:
            picks.append(str(file_path))
    return picks


def _load_recents() -> List[str]:
    if RECENTS_PATH.exists():
        try:
            return json.loads(RECENTS_PATH.read_text())
        except Exception:
            return []
    return []


def _save_recent(topic: str) -> None:
    recents = _load_recents()
    if topic in recents:
        recents.remove(topic)
    recents.insert(0, topic)
    recents = recents[:10]
    RECENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECENTS_PATH.write_text(json.dumps(recents, indent=2))


def _load_bundles() -> dict[str, List[str]]:
    if not TOPICS_YAML.exists() or yaml is None:
        return {}
    data = yaml.safe_load(TOPICS_YAML.read_text()) or {}
    bundles = data.get("bundles", {}) or {}
    return {str(key): list(value) for key, value in bundles.items()}


def _pick(prompt: str, items: List[str]) -> str | None:
    print(prompt)
    for idx, value in enumerate(items, start=1):
        print(f" {idx}) {value}")
    print(" 0) Back")
    selection = input("Select > ").strip()
    if not selection.isdigit():
        return None
    pos = int(selection)
    if pos == 0:
        return None
    if 1 <= pos <= len(items):
        return items[pos - 1]
    return None


def _run_topic_direct(topic: str) -> int:
    picks = _match_files_by_topic(topic)
    if not picks:
        print(f"No matching test files for topic: {topic}")
        print("Tip: include 'api' to allow FastAPI tests, or try a broader term.")
        input("\nPress Enter to return to menu...")
        return 2

    print(f"Selected files ({len(picks)}):")
    for path in picks:
        print("  ", path)

    reports_dir = Path("test_core/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    junit = reports_dir / "_topic_ui.xml"
    cmd = [
        "pytest",
        *sorted(set(picks)),
        "--maxfail=1",
        "--junitxml",
        str(junit),
        "-q",
    ]
    env = os.environ.copy()
    repo_root = str(Path(__file__).resolve().parents[1])
    backend = str(Path(repo_root) / "backend")
    env["PYTHONPATH"] = os.pathsep.join([
        repo_root,
        backend,
        env.get("PYTHONPATH", ""),
    ]).strip(os.pathsep)
    print("Running:", " ".join(shlex.quote(arg) for arg in cmd))
    rc = subprocess.call(cmd, env=env)
    _save_recent(topic)
    input("\nPress Enter to return to menu...")
    return rc


def run_ui() -> None:
    while True:
        print("\n==============================")
        print(" 🔎 Topic Test Runner")
        print("==============================")
        print(" 1) Run by Topic…   (hint: you can also just type your topic at the prompt)")
        print(" 2) Run Bundle…")
        print(" 3) Recent Topics…")
        print(" 0) Exit")
        choice = input("Select > ").strip()
        if choice and not choice.isdigit():
            topic = choice
            if topic.lower() in {"exit", "quit"}:
                return
            _run_topic_direct(topic)
            continue

        if choice == "1":
            topic = input("Topic word/phrase > ").strip()
            if topic:
                _run_topic_direct(topic)
        elif choice == "2":
            bundles = _load_bundles()
            if not bundles:
                print("No bundles found. Create test_core/topics.yaml.")
                input("Press Enter…")
                continue
            selection = _pick("Pick a bundle:", list(bundles.keys()))
            if selection:
                query = " ".join(bundles[selection])
                _run_topic_direct(query)
        elif choice == "3":
            recents = _load_recents()
            if not recents:
                print("No recent topics yet.")
                input("Press Enter to return…")
                continue
            selection = _pick("Pick a recent topic:", recents)
            if selection:
                _run_topic_direct(selection)
        elif choice == "0":
            return
        else:
            print("Invalid selection.")
