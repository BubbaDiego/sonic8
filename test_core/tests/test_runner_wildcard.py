from pathlib import Path
import pytest

from test_core.runner import TestCoreRunner


def test_wildcard_pattern(tmp_path):
    (tmp_path / "test_one.py").write_text("def test_one():\n    assert True\n")
    (tmp_path / "test_two.py").write_text("def test_two():\n    assert True\n")

    runner = TestCoreRunner(root=tmp_path)
    result = runner.run(str(tmp_path / "test_*.py"))

    assert result["passed"] == 2
    assert result["failed"] == 0
    assert result["grade"] == "A+"
    report = Path(result["failure_report"])
    assert report.exists()


def test_wildcard_no_match(tmp_path):
    runner = TestCoreRunner(root=tmp_path)
    with pytest.warns(UserWarning):
        result = runner.run(str(tmp_path / "test_*.py"))

    assert result["grade"] == "F"
    assert result["total"] == 0
    report = Path(result["failure_report"])
    assert report.exists()
