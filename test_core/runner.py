"""Run pytest programmatically and write concise failure reports.

This module implements :class:`TestCoreRunner` which mirrors the design
outlined in ``test_core/test_core_spec.md``.  The previous revision contained only a
minimal stub that shell'ed out to ``pytest``.  The runner now executes tests
in-process, writes one failure file per test case (plus an aggregated
``ALL_FAILURES.txt``) and returns a summary dictionary including the overall
grade.
"""
from __future__ import annotations
import importlib.util
import json
import os
import re
import shutil
import sys
from typing import Any
from pathlib import Path
import glob
import warnings
import pytest
from .formatter import grade_from_pct
from .icons import ICON_MAP
try:  # optional celebration output
    from .celebrations import celebrate_grade  # type: ignore
except Exception:  # pragma: no cover - optional dependency might be missing
    celebrate_grade = None


class TestCoreRunner:
    """Run tests using pytest programmatically."""

    def __init__(self, root: str | Path | None = None, html: bool = False) -> None:
        self.root = Path(root or __file__).parent
        self.fail_dir = self.root / "failures"
        self.reports_dir = self.root / "reports"
        self.fail_dir.mkdir(exist_ok=True, parents=True)
        self.reports_dir.mkdir(exist_ok=True, parents=True)
        self.html = html
        self.last_results: dict[str, Any] | None = None

    # ----------------------------------------------------------------- helpers
    def _clear_failures(self) -> None:
        if self.fail_dir.exists():
            shutil.rmtree(self.fail_dir)
        self.fail_dir.mkdir(parents=True, exist_ok=True)

    def _slugify(self, raw: str) -> str:
        """Sanitize *raw* for use in file names."""
        slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("_")
        return slug or "pattern"

    def _write_pattern_report(
        self, pattern: str, tests: list[dict[str, str]], results: dict[str, Any]
    ) -> Path:
        """Write aggregated failure report for *pattern* and return path."""
        slug = self._slugify(pattern)
        out_path = self.reports_dir / f"{slug}_failures.txt"
        lines = [
            f"Pattern: {pattern}",
            f"Passed: {results.get('passed',0)} | Failed: {results.get('failed',0)} | Skipped: {results.get('skipped',0)}",
            "",
        ]
        for t in tests:
            if t.get("outcome") == "passed":
                continue
            nodeid = t.get("nodeid", "unknown")
            tb = t.get("longrepr", "") or ""
            lines.append(f"## {nodeid}")
            lines.append(tb)
            lines.append("")
        out_path.write_text("\n".join(lines), encoding="utf-8")
        return out_path

    def _bootstrap(self) -> None:
        """Import the local ``tests.conftest`` to register dependency stubs."""
        conf = self.root / "tests" / "conftest.py"
        if not conf.exists():
            return
        # Use a unique module name to avoid ImportPathMismatch errors when the
        # repository also includes ``test_core/conftest.py``.  Pytest requires
        # the actual filename ``conftest.py`` but the module name can be
        # arbitrary.  Importing under a different name keeps both files loaded
        # without conflicts.
        spec = importlib.util.spec_from_file_location(
            "test_core.tests_bootstrap", conf
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules.setdefault(spec.name, module)
            spec.loader.exec_module(module)

    def _build_pytest_args(self, files: list[str]) -> list[str]:
        json_report = self.reports_dir / "last_test_report.json"
        args = [*files, "-vv", "-s"]
        if importlib.util.find_spec("pytest_jsonreport"):
            args += ["-p", "pytest_jsonreport", f"--json-report-file={json_report}"]
        if self.html and importlib.util.find_spec("pytest_html"):
            html_report = self.reports_dir / "last_test_report.html"
            args += [
                "-p",
                "pytest_metadata.plugin",
                "-p",
                "pytest_html.plugin",
                "--html",
                str(html_report),
                "--self-contained-html",
            ]
        os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
        return args

    # ----------------------------------------------------------------- public
    def run(self, pattern: str | None = None) -> dict[str, Any]:
        """Execute tests matching *pattern* and return a summary dict."""
        pattern = self._expand(pattern or str(self.root / "tests" / "test_*.py"))
        files = sorted(glob.glob(pattern, recursive=True))
        if not files:
            warnings.warn(f"Pattern matched no files: {pattern}")
            results = {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "grade": "F",
                "total": 0,
                "pct": 0.0,
            }
            report = self._write_pattern_report(pattern, [], results)
            results["failure_report"] = str(report)
            self.last_results = results
            return results
        self._bootstrap()
        self._clear_failures()
        args = self._build_pytest_args(files)
        collector: list[dict[str, str]] = []

        class _Plugin:
            def pytest_runtest_logreport(self, report):
                if report.when == "call":
                    collector.append(
                        {
                            "nodeid": report.nodeid,
                            "outcome": report.outcome,
                            "longrepr": getattr(
                                report, "longreprtext", str(report.longrepr)
                            ),
                        }
                    )

        pytest.main(args, plugins=[_Plugin()])
        tests = collector
        passed = sum(1 for t in tests if t.get("outcome") == "passed")
        failed = sum(1 for t in tests if t.get("outcome") not in {"passed", "skipped"})
        skipped = sum(1 for t in tests if t.get("outcome") == "skipped")
        total = passed + failed + skipped
        pct = passed / total * 100 if total else 0
        grade = grade_from_pct(pct)
        results = {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "grade": grade,
            "total": total,
            "pct": pct,
        }
        for t in tests:
            if t.get("outcome") == "passed":
                continue
            nodeid = t.get("nodeid", "unknown")
            name = nodeid.split("::")[-1] or "unknown"
            tb_lines = (t.get("longrepr", "") or "").splitlines()[:25]
            (self.fail_dir / f"{name}_fail.txt").write_text(
                "\n".join(tb_lines), encoding="utf-8"
            )
            with (self.fail_dir / "ALL_FAILURES.txt").open(
                "a", encoding="utf-8"
            ) as agg:
                agg.write(f"# {name}\n")
                agg.write("\n".join(tb_lines))
                agg.write("\n\n")
        summary = self.reports_dir / "summary.json"
        summary.write_text(json.dumps(results, indent=2), encoding="utf-8")
        report = self._write_pattern_report(pattern, tests, results)
        results["failure_report"] = str(report)
        self.last_results = results
        if celebrate_grade and grade:
            try:
                celebrate_grade(grade)
            except Exception:
                pass
        return results

    # ----------------------------------------------------------------- utils
    def _expand(self, raw: str) -> str:
        """Translate short aliases like 'alerts' into glob pattern."""
        if raw.lower() == "alerts":
            return str(self.root / "tests" / "test_*alert*.py")
        if os.sep in raw or raw.startswith("test_") or "*" in raw:
            return str(raw)
        return str(self.root / "tests" / f"test_{raw}*.*")
