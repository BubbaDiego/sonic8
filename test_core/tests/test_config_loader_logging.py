import pytest
from alert_core.config.loader import load_thresholds, ConfigError
from alert_core.infrastructure.stores import AlertLogStore, _DBAdapter
import alert_core.infrastructure.stores as stores
from types import SimpleNamespace
import alert_core.domain.models as models


def test_load_thresholds_logs_missing(tmp_path):
    store = AlertLogStore(_DBAdapter(str(tmp_path / "log.db")))
    models.AlertLog = SimpleNamespace
    stores.AlertLog = SimpleNamespace
    import alert_core.config.loader as loader
    loader.AlertLog = SimpleNamespace
    with pytest.raises(ConfigError):
        load_thresholds(tmp_path / "missing.json", log_store=store)
    logs = store.list()
    assert len(logs) == 1
