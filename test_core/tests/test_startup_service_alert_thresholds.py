import json
import importlib

import pytest

from utils import startup_service as ss
from utils.schema_validation_service import SchemaValidationService


def test_ensure_alert_thresholds_valid(tmp_path, monkeypatch):
    valid_file = tmp_path / "alert_thresholds.json"
    valid_data = {
        "alert_ranges": {
            "liquidation_distance_ranges": {},
            "travel_percent_liquid_ranges": {},
            "heat_index_ranges": {},
            "profit_ranges": {},
            "price_alerts": {},
        },
        "cooldowns": {
            "alert_cooldown_seconds": 300,
            "call_refractory_period": 900,
            "snooze_countdown": 300,
        },
        "notifications": {
            "heat_index": {"low": {}, "medium": {}, "high": {}}
        },
    }

    with open(valid_file, "w", encoding="utf-8") as f:
        json.dump(valid_data, f)

    importlib.reload(ss)
    monkeypatch.setattr(ss, "ALERT_THRESHOLDS_PATH", valid_file)
    monkeypatch.setattr(SchemaValidationService, "ALERT_THRESHOLDS_FILE", str(valid_file))

    ss.StartUpService.ensure_alert_thresholds()


def test_ensure_alert_thresholds_creates_default_with_source(tmp_path, monkeypatch):
    default_file = tmp_path / "alert_thresholds.json"

    importlib.reload(ss)
    monkeypatch.setattr(ss, "ALERT_THRESHOLDS_PATH", default_file)
    import config.config_loader as cfg
    monkeypatch.setattr(cfg, "ALERT_THRESHOLDS_PATH", default_file)
    monkeypatch.setattr(SchemaValidationService, "ALERT_THRESHOLDS_FILE", str(default_file))

    ss.StartUpService.ensure_alert_thresholds()

    with open(default_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("source") == "fallback"


def test_ensure_alert_thresholds_creates_valid_default(tmp_path, monkeypatch):
    """The generated default file should pass schema validation."""
    default_file = tmp_path / "alert_thresholds.json"

    importlib.reload(ss)
    monkeypatch.setattr(ss, "ALERT_THRESHOLDS_PATH", default_file)
    import config.config_loader as cfg
    monkeypatch.setattr(cfg, "ALERT_THRESHOLDS_PATH", default_file)
    monkeypatch.setattr(SchemaValidationService, "ALERT_THRESHOLDS_FILE", str(default_file))

    ss.StartUpService.ensure_alert_thresholds()

    assert SchemaValidationService.validate_schema(
        str(default_file), SchemaValidationService.ALERT_THRESHOLDS_SCHEMA
    )


def test_ensure_alert_thresholds_default_validation_failure(tmp_path, monkeypatch):
    """If the default file fails validation startup should abort."""
    default_file = tmp_path / "alert_thresholds.json"

    importlib.reload(ss)
    monkeypatch.setattr(ss, "ALERT_THRESHOLDS_PATH", default_file)
    import config.config_loader as cfg
    monkeypatch.setattr(cfg, "ALERT_THRESHOLDS_PATH", default_file)
    monkeypatch.setattr(SchemaValidationService, "ALERT_THRESHOLDS_FILE", str(default_file))

    # Force validation to fail
    monkeypatch.setattr(SchemaValidationService, "validate_schema", lambda *a, **k: False)

    with pytest.raises(SystemExit):
        ss.StartUpService.ensure_alert_thresholds()

