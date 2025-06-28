"""Interactive console UI for running tests.

Author: BubbaDiego

This is a lightweight implementation of the menu described in
``test_core/test_core_spec.md``. Rich-based widgets will be introduced later; for now
it relies on plain ``input``/``print`` calls so it works in minimal
environments.
"""
from __future__ import annotations

from typing import Optional

from test_core.runner import TestCoreRunner
from test_core.formatter import render_summary
from test_core.icons import ICON_MAP

MENU_ITEMS = [
    ("1", "🚀 Run All tests", "tests"),
    ("2", "🔍 Run Pattern…", None),
    ("3", "🧹 Clear failures dir", "clear"),
    ("4", "📊 Show last summary", "summary"),
    ("5", "🚪 Exit", "exit"),
]


class TestConsoleUI:
    """Simple text-based console interface."""

    def __init__(self, runner: Optional[TestCoreRunner] = None) -> None:
        self.runner = runner or TestCoreRunner()

    # ------------------------------------------------------------------ helpers
    def _run_pattern(self, pattern: str) -> None:
        results = self.runner.run(pattern)
        print(render_summary(results))

    def _show_summary(self) -> None:
        if self.runner.last_results is None:
            print("No summary available.")
        else:
            print(render_summary(self.runner.last_results))

    # ------------------------------------------------------------------ public
    def start(self) -> None:
        while True:
            print("\n" + ICON_MAP.get("banner"))
            for key, label, _ in MENU_ITEMS:
                print(f" {key}) {label}")
            choice = input("Select > ").strip()
            if choice == "1":
                self._run_pattern(str(self.runner.root / "tests" / "test_*.py"))
            elif choice == "2":
                glob = input("Enter wildcard pattern > ").strip()
                self._run_pattern(glob)
            elif choice == "3":
                self.runner._clear_failures()
                print("Failures directory cleared.")
            elif choice == "4":
                self._show_summary()
            elif choice == "5":
                break
            else:
                print("Invalid selection.")


def main() -> None:
    TestConsoleUI().start()


if __name__ == "__main__":
    main()
