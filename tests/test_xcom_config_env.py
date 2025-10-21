import json
import backend.utils.env_utils as env_utils
from backend.data.data_locker import DataLocker
from backend.core.xcom_core.xcom_config_service import XComConfigService


def test_xcom_config_resolves_env(tmp_path, monkeypatch):
    config_dir = tmp_path
    (config_dir / "comm_config.json").write_text(
        json.dumps(
            {
                "communication": {
                    "providers": {
                        "email": {
                            "enabled": True,
                            "smtp": {
                                "server": "${SMTP_SERVER}",
                                "port": "${SMTP_PORT}",
                                "username": "${SMTP_USERNAME}",
                                "password": "${SMTP_PASSWORD}",
                                "default_recipient": "${SMTP_DEFAULT_RECIPIENT}"
                            }
                        }
                    }
                }
            }
        )
    )
    monkeypatch.setattr("backend.data.data_locker.CONFIG_DIR", config_dir)

    monkeypatch.setenv("SMTP_SERVER", "mail.example.com")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_USERNAME", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "pass")
    monkeypatch.setenv("SMTP_DEFAULT_RECIPIENT", "to@example.com")

    orig = env_utils._resolve_env
    monkeypatch.setattr(env_utils, "_resolve_env", lambda v, k: v)
    monkeypatch.setattr("backend.data.data_locker._resolve_env", lambda v, k: v)
    dl = DataLocker(str(tmp_path / "test.db"))
    monkeypatch.setattr(env_utils, "_resolve_env", orig)
    monkeypatch.setattr("backend.data.data_locker._resolve_env", orig)

    cfg = dl.system.get_var("xcom_providers")
    assert cfg["email"]["smtp"]["server"] == "${SMTP_SERVER}"

    svc = XComConfigService(dl)
    provider = svc.get_provider("email")
    smtp = provider["smtp"]
    assert smtp["server"] == "mail.example.com"
    assert smtp["port"] == "465"
    assert smtp["username"] == "user"
    assert smtp["password"] == "pass"
    assert smtp["default_recipient"] == "to@example.com"


def test_xcom_config_resolves_alexa_env(tmp_path, monkeypatch):
    config_dir = tmp_path
    (config_dir / "comm_config.json").write_text(
        json.dumps(
            {
                "communication": {
                    "providers": {
                        "alexa": {
                            "enabled": "${ALEXA_ENABLED}",
                            "access_code": "${ALEXA_ACCESS_CODE}",
                        }
                    }
                }
            }
        )
    )
    monkeypatch.setattr("backend.data.data_locker.CONFIG_DIR", config_dir)

    monkeypatch.setenv("ALEXA_ENABLED", "true")
    monkeypatch.setenv("ALEXA_ACCESS_CODE", "code123")

    orig = env_utils._resolve_env
    monkeypatch.setattr(env_utils, "_resolve_env", lambda v, k: v)
    monkeypatch.setattr("backend.data.data_locker._resolve_env", lambda v, k: v)
    dl = DataLocker(str(tmp_path / "test.db"))
    monkeypatch.setattr(env_utils, "_resolve_env", orig)
    monkeypatch.setattr("backend.data.data_locker._resolve_env", orig)

    svc = XComConfigService(dl)
    provider = svc.get_provider("alexa")
    assert provider["enabled"] == "true"
    assert provider["access_code"] == "code123"


def test_channels_for_defaults_ignore_global(tmp_path, monkeypatch):
    monkeypatch.setattr("backend.core.xcom_core.xcom_config_service.C.get_xcom_live", lambda: False)
    dl = DataLocker(str(tmp_path / "test.db"))
    svc = XComConfigService(dl)

    dl.system.set_var(
        "xcom_providers",
        {
            "global": {"voice": True, "system": False},
            "profit": {"sms": True},
        },
    )

    profit_channels = svc.channels_for("profit")
    assert profit_channels == {"live": False, "system": True, "voice": False, "sms": True, "tts": False}

    market_channels = svc.channels_for("market")
    assert market_channels == {"live": False, "system": True, "voice": False, "sms": False, "tts": False}
