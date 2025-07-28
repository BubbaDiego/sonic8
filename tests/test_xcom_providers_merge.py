import json
from backend.data.data_locker import DataLocker


def test_xcom_providers_merge(tmp_path, monkeypatch):
    config_dir = tmp_path
    (config_dir / "comm_config.json").write_text(
        json.dumps(
            {
                "communication": {
                    "providers": {
                        "sms": {"enabled": False},
                        "tts": {}
                    }
                }
            }
        )
    )
    monkeypatch.setattr("backend.data.data_locker.CONFIG_DIR", config_dir)
    dl = DataLocker(str(tmp_path / "test.db"))
    cfg = dl.system.get_var("xcom_providers")
    assert cfg["sms"]["enabled"] is False
    assert cfg["tts"]["enabled"] is True
    dl.close()

    (config_dir / "comm_config.json").write_text(
        json.dumps(
            {
                "communication": {
                    "providers": {
                        "sms": {"enabled": True, "carrier": "foo"},
                        "new": {"foo": "bar"}
                    }
                }
            }
        )
    )
    dl2 = DataLocker(str(tmp_path / "test.db"))
    cfg2 = dl2.system.get_var("xcom_providers")
    assert cfg2["sms"]["enabled"] is True
    assert cfg2["sms"]["carrier"] == "foo"
    assert cfg2["tts"]["enabled"] is True  # preserved
    assert cfg2["new"]["foo"] == "bar"
