from pathlib import Path

from test_core.runner import TestCoreRunner


def test_failure_files(tmp_path):
    test_file = tmp_path / "test_fail.py"
    test_file.write_text("def test_fail():\n    assert False\n")

    runner = TestCoreRunner(root=tmp_path)
    result = runner.run(str(test_file))

    fail_file = runner.fail_dir / "test_fail_fail.txt"
    assert fail_file.exists()
    lines = fail_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) <= 25
    assert result["failed"] == 1
    report_path = Path(result["failure_report"])
    assert report_path.exists()
    text = report_path.read_text(encoding="utf-8")
    assert "test_fail.py::test_fail" in text
