from test_core.runner import TestCoreRunner, celebrate_grade


def test_run_invokes_celebration(tmp_path, monkeypatch):
    test_file = tmp_path / "test_ok.py"
    test_file.write_text("def test_ok():\n    assert True\n")

    called = []
    monkeypatch.setattr("test_core.runner.celebrate_grade", lambda g: called.append(g))

    runner = TestCoreRunner(root=tmp_path)
    result = runner.run(str(test_file))

    assert called == [result["grade"]]
