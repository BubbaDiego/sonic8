from pathlib import Path
from typing import List
import os
import sys
import importlib
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from test_core.test_core import TestCore


def test_run_glob_filters_virtual_envs(tmp_path, monkeypatch):
    # Set up directory structure with various test files
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "test_valid.py").write_text("")

    for d in [".venv", "venv", "site-packages"]:
        (tmp_path / d).mkdir()
        (tmp_path / d / "test_ignore.py").write_text("")

    captured: List[Path] = []

    def fake_run_files(self, files):
        captured.extend(files)

    tc = TestCore()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(TestCore, "run_files", fake_run_files)

    tc.run_glob("test_*.py")

    assert captured == [Path("sub/test_valid.py")]


def test_run_glob_skips_pycache_and_pyc(tmp_path, monkeypatch):
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "test_cache.py").write_text("")
    (tmp_path / "test_ok.py").write_text("")
    (tmp_path / "test_skip.pyc").write_text("")

    captured: List[Path] = []

    def fake_run_files(self, files):
        captured.extend(files)

    tc = TestCore()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(TestCore, "run_files", fake_run_files)

    tc.run_glob("test*")

    assert captured == [Path("test_ok.py")]


def test_run_files_filters_non_py(tmp_path, monkeypatch):
    tc = TestCore(report_dir=tmp_path)
    (tmp_path / "good.py").write_text("print('ok')")
    (tmp_path / "bad.pyc").write_text("")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "cache.py").write_text("")

    captured_args = []

    def fake_pytest_main(args):
        captured_args.extend(args)
        return 0

    monkeypatch.setattr(TestCore, "_open_html_report", lambda self, p: None)
    monkeypatch.setattr("pytest.main", fake_pytest_main)

    tc.run_files([tmp_path / "good.py", tmp_path / "bad.pyc", tmp_path / "__pycache__" / "cache.py"])

    assert captured_args[0] == str(tmp_path / "good.py")
    assert len(captured_args) > 0 and str(tmp_path / "bad.pyc") not in captured_args
    assert str(tmp_path / "__pycache__" / "cache.py") not in captured_args


def test_run_files_writes_failure_file(tmp_path, monkeypatch):
    tc = TestCore(report_dir=tmp_path)
    (tmp_path / "fail.py").write_text("print('bad')")

    def fake_pytest_main(args):
        (tmp_path / "last_test_report.json").write_text(
            json.dumps(
                {
                    "tests": [
                        {
                            "nodeid": "test_core/tests/fail.py::test_a",
                            "outcome": "failed",
                            "longrepr": "AssertionError: boom",
                        }
                    ]
                }
            )
        )
        print("FAILED test_core/tests/fail.py::test_a")
        return 1

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(TestCore, "_open_html_report", lambda self, p: None)
    monkeypatch.setattr("pytest.main", fake_pytest_main)

    tc.run_files([tmp_path / "fail.py"])

    failure_path = tmp_path / "failures.txt"
    assert failure_path.exists()
    text = failure_path.read_text()
    assert "test_core/tests/fail.py::test_a" in text
    assert "FAILED" in text
    detail_dir = Path("reports/test_failures")
    detail_file = detail_dir / "test_a_fail.txt"
    assert detail_file.exists(), "expected detailed failure file"
    text = detail_file.read_text()
    assert "test_core/tests/fail.py::test_a" in text
    assert "AssertionError" in text



def test_run_files_clears_failure_file(tmp_path, monkeypatch):
    tc = TestCore(report_dir=tmp_path)
    (tmp_path / "ok.py").write_text("print('ok')")

    def fake_pytest_main(args):
        (tmp_path / "last_test_report.json").write_text(
            json.dumps({"tests": [{"nodeid": "test_core/tests/ok.py::test_a", "outcome": "passed", "longrepr": ""}]})
        )
        print("PASSED test_core/tests/ok.py::test_a")
        return 0

    monkeypatch.chdir(tmp_path)
    (tmp_path / "failures.txt").write_text("old")

    detail_dir = Path("reports/test_failures")
    detail_dir.mkdir(parents=True)
    (detail_dir / "old_fail.txt").write_text("old")


    monkeypatch.setattr(TestCore, "_open_html_report", lambda self, p: None)
    monkeypatch.setattr("pytest.main", fake_pytest_main)

    tc.run_files([tmp_path / "ok.py"])

    assert not (tmp_path / "failures.txt").exists()

    assert not detail_dir.exists()



def test_run_files_html_plugin_disabled_by_default(tmp_path, monkeypatch):
    tc = TestCore(report_dir=tmp_path)
    test_file = tmp_path / "test_ok.py"
    test_file.write_text("def test_ok():\n    assert True\n")

    import types
    plugin = types.ModuleType("pytest_html")

    def pytest_addoption(parser):
        parser.addoption("--html", action="store")

    plugin.pytest_addoption = pytest_addoption
    sys.modules["pytest_html"] = plugin

    def fake_find_spec(name):
        if name == "pytest_html":
            from importlib.machinery import ModuleSpec
            return ModuleSpec(name, loader=None)
        return None

    captured_args = []
    orig_main = pytest.main

    def capture_main(args):
        captured_args.extend(args)
        return orig_main(args)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    monkeypatch.setattr(TestCore, "_open_html_report", lambda self, p: None)
    monkeypatch.setattr(pytest, "main", capture_main)

    tc.run_files([test_file])

    assert "--html" not in captured_args
    assert "pytest_html" not in captured_args
    assert tc.last_results["failed"] == 0
