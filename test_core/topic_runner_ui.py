"""Interactive menu for the Topic Test Runner."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

from .topic_console import main as topic_main

RECENTS_PATH = Path("test_core/reports/_recent_topics.json")
TOPICS_YAML = Path("test_core/topics.yaml")


def _load_recents() -> List[str]:
    if RECENTS_PATH.exists():
        try:
            return json.loads(RECENTS_PATH.read_text())
        except Exception:
            return []
    return []


def _save_recent(topics: Iterable[str]) -> None:
    recents = _load_recents()
    for topic in topics:
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
    return {str(k): list(v) for k, v in bundles.items()}


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


def _run_topics(topics: List[str]) -> None:
    argv: List[str] = []
    for topic in topics:
        argv += ["--topic", topic]
    argv.append("--quiet")
    try:
        topic_main(argv)
    finally:
        _save_recent(topics)
        input("\nPress Enter to return to the Topic Test Runner…")


def run_ui() -> None:
    while True:
        print("\n==============================")
        print(" 🔎 Topic Test Runner")
        print("==============================")
        print(" 1) Run by Topic…")
        print(" 2) Run Bundle…")
        print(" 3) Recent Topics…")
        print(" 0) Exit")
        choice = input("Select > ").strip()
        # Quick-run: if you type a topic here (not a number), we just run it.
        if choice and not choice.isdigit():
            topic = choice
            if topic.lower() in {"exit", "quit"}:
                return
            _run_topics([topic])
            continue

        if choice == "1":
            topic = input("Topic word/phrase > ").strip()
            if topic:
                _run_topics([topic])
        elif choice == "2":
            bundles = _load_bundles()
            if not bundles:
                print("No bundles found. Create test_core/topics.yaml with a bundles section.")
                input("Press Enter to return…")
                continue
            selection = _pick("Pick a bundle:", list(bundles.keys()))
            if selection:
                _run_topics(bundles[selection])
        elif choice == "3":
            recents = _load_recents()
            if not recents:
                print("No recent topics yet.")
                input("Press Enter to return…")
                continue
            selection = _pick("Pick a recent topic:", recents)
            if selection:
                _run_topics([selection])
        elif choice == "0":
            return
        else:
            print("Invalid selection.")
