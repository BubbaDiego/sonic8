from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from core.logging import log

try:  # pragma: no cover - optional dependency
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
except Exception:  # pragma: no cover - fallback if Rich missing
    Console = Panel = Table = None
    console = None

__all__ = ["TestCore", "TestCoreConsole"]


class TestCore:
    """Run pytest and track failures."""

    def __init__(self, report_dir: str | Path | None = None, default_pattern: str = "test_core/tests/test_*.py", html: bool = False) -> None:
        base = Path(__file__).parent
        self.report_dir = Path(report_dir or base / "reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.fail_dir = base / "failures"
        self.fail_dir.mkdir(parents=True, exist_ok=True)
        self.default_pattern = default_pattern
        self.enable_html = html
        self.last_results: dict[str, object] = {}

    # ------------------------------------------------------------------ utils
    def clear_failures_directory(self) -> None:
        if self.fail_dir.exists():
            import shutil
            shutil.rmtree(self.fail_dir)
        self.fail_dir.mkdir(parents=True, exist_ok=True)

    def store_failure(self, test_file_name: str, traceback: str) -> None:
        self.fail_dir.mkdir(parents=True, exist_ok=True)
        (self.fail_dir / f"{test_file_name}_fail.txt").write_text(traceback, encoding="utf-8")

    # ------------------------------------------------------------------ runners
    def run_all_tests(self) -> None:
        self.run_glob(self.default_pattern)

    def run_alert_tests(self) -> None:
        self.run_glob("test_core/tests/test_*alert*.py")

    def run_report(self) -> None:
        self.run_all_tests()
        if self.enable_html and console:
            report = self.report_dir / "summary_report.html"
            self._open_html_report(report)

    def expand_pattern(self, raw: str) -> str:
        if "*" in raw or raw.startswith("test_"):
            return raw
        return f"test_{raw}*.*"

    def run_glob(self, pattern: str | None = None) -> None:
        pattern = self.expand_pattern(pattern or self.default_pattern)
        files = [p for p in Path("").rglob(pattern) if p.suffix == ".py" and "__pycache__" not in p.parts]
        if not files:
            log.warning(f"⚠️ No test files found for pattern: {pattern}", source="TestCore")
            return
        self.run_files(files)

    def run_files(self, files: list[str | Path]) -> None:
        html_report = self.report_dir / "last_test_report.html"
        json_report = self.report_dir / "last_test_report.json"

        self.clear_failures_directory()

        args = [*(str(Path(f)) for f in files), "-vv", "-s"]

        if importlib.util.find_spec("pytest_jsonreport") is not None:
            args += [
                "-p",
                "pytest_jsonreport",
                "--json-report",
                f"--json-report-file={json_report}",
            ]

        html_spec = importlib.util.find_spec("pytest_html")
        if self.enable_html and html_spec is not None:
            if importlib.util.find_spec("pytest_metadata") is not None:
                args += ["-p", "pytest_metadata"]
            args += [
                "-p",
                "pytest_html.plugin",
                "--html",
                str(html_report),
                "--self-contained-html",
            ]

        os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        result = pytest.main(args)

        if not json_report.exists():
            log.warning("JSON report missing", source="TestCore")
            return

        data = json.loads(json_report.read_text(encoding="utf-8"))
        tests = data.get("tests", [])
        passed = sum(1 for t in tests if t.get("outcome") == "passed")
        failed = sum(1 for t in tests if t.get("outcome") not in {"passed", "skipped"})
        skipped = sum(1 for t in tests if t.get("outcome") == "skipped")
        for t in tests:
            if t.get("outcome") == "passed":
                continue
            nodeid = t.get("nodeid", "unknown")
            case_name = nodeid.split("::")[-1]
            tb_lines = t.get("longrepr", "")
            self.store_failure(case_name, tb_lines)

        total = passed + failed + skipped
        grade = None
        if total:
            pct = passed / total * 100
            if pct == 100:
                grade = "A+"
            elif pct >= 90:
                grade = "A"
            elif pct >= 80:
                grade = "B"
            elif pct >= 70:
                grade = "C"
            elif pct >= 60:
                grade = "D"
            else:
                grade = "F"
            log.info(f"🔢 Pass Rate: {pct:.1f}% ({passed}/{total})", source="TestCore")

        self.last_results = {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "grade": grade,
            "html_report": str(html_report),
        }

        self._write_summary_html()
        if self.enable_html and console:
            self._open_html_report(self.report_dir / "summary_report.html")

    # ------------------------------------------------------------------ helpers
    def _write_summary_html(self) -> None:
        res = self.last_results
        html_report = Path(res.get("html_report", ""))
        summary_path = self.report_dir / "summary_report.html"
        total = res.get("passed", 0) + res.get("failed", 0) + res.get("skipped", 0)
        score = res.get("grade") or "N/A"
        iframe = (
            f"<iframe src='{html_report.name}' width='100%' height='800' style='border:none;'></iframe>"
            if self.enable_html and html_report.exists()
            else ""
        )
        summary_html = f"""
        <html><head><title>Test Report</title></head>
        <body>
        <h1>Sonic Test Summary</h1>
        <p>Passed: {res.get('passed',0)} | Failed: {res.get('failed',0)} | Skipped: {res.get('skipped',0)}</p>
        <p>Total: {total} | Score: {score}</p>
        {iframe}
        </body></html>
        """
        summary_path.write_text(summary_html, encoding="utf-8")

    def export_codex_failures(
        self,
        target_dir: str | Path = "reports/codex_failures",
        max_tb_lines: int = 25,
        clear_dir: bool = False,
    ) -> None:
        """Create one text file per failing test for Codex."""

        json_path = self.report_dir / "last_test_report.json"
        if not json_path.exists():
            return

        data = json.loads(json_path.read_text(encoding="utf-8"))
        failures = [t for t in data.get("tests", []) if t.get("outcome") != "passed"]
        out_dir = Path(target_dir)
        if clear_dir and out_dir.exists():
            import shutil
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        for t in failures:
            nodeid = t.get("nodeid", "unknown")
            case_name = nodeid.split("::")[-1] or "unknown"
            safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", case_name)
            fn = out_dir / f"{safe_name}_fail.txt"
            counter = 2
            while fn.exists():
                fn = out_dir / f"{safe_name}_{counter}_fail.txt"
                counter += 1

            tb_lines = (t.get("longrepr", "") or "").splitlines()[:max_tb_lines]
            body = "\n".join(tb_lines) or "*no traceback*"
            content = f"{nodeid}\n{body}\n"
            fn.write_text(content, encoding="utf-8")


    def _open_html_report(self, report_path: Path) -> None:
        if not report_path.exists():
            return
        try:
            import webbrowser
            webbrowser.open(report_path.resolve().as_uri())
        except Exception:
            pass


class TestCoreConsole:
    """Interactive console for running tests."""

    def interactive_menu(self) -> None:
        tester = TestCore(html=True)
        while True:
            if console:
                console.clear()
                console.print(Panel("[bold blue]🔬 Test Core Console[/bold blue]", border_style="blue"))
                table = Table(show_header=False, box=None)
                table.add_column("#", style="cyan", justify="right")
                table.add_column("Action", style="white")
                table.add_row("1", "📋 Run All Tests")
                table.add_row("2", "🔔 Run Alert Tests")
                table.add_row("3", "📑 Show Test Report")
                table.add_row("4", "🗂️ Clear Failures Directory")
                table.add_row("5", "⚙️ Setup Environment")
                table.add_row("6", "🔙 Exit to Launch Pad")
                console.print(table)
                choice = console.input("Choose > ").strip()
            else:
                os.system("cls" if os.name == "nt" else "clear")
                print("1) Run All Tests")
                print("2) Run Alert Tests")
                print("3) Show Test Report")
                print("4) Clear Failures Directory")
                print("5) Setup Environment")
                print("6) Exit")
                choice = input("Choose > ").strip()

            if choice == "1":
                tester.run_all_tests()
            elif choice == "2":
                tester.run_alert_tests()
            elif choice == "3":
                tester.run_report()
            elif choice == "4":
                tester.clear_failures_directory()
                print("Failures cleared")
            elif choice == "5":
                self.setup_environment()

            elif choice == "6":
                break
            else:
                if console:
                    console.print("Invalid choice. Try again.")
                else:
                    print("Invalid choice.")
                continue
            if console:
                console.input("\n[grey]Press ENTER to continue...[/grey]")
            else:
                input("Press ENTER to continue...")

    # simple dependency installer
    def setup_environment(self) -> None:
        req = Path("requirements.txt")
        if not req.exists():
            log.error("requirements.txt not found", source="TestCore")
            return
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req)])
            log.success("Dependencies installed", source="TestCore")
        except Exception as exc:  # pragma: no cover - network dependent
            log.error(f"Dependency installation failed: {exc}", source="TestCore")
