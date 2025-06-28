from datetime import datetime

from alert_core.infrastructure.stores import AlertLogStore, _DBAdapter
from types import SimpleNamespace
import alert_core.domain.models as models
import alert_core.infrastructure.stores as stores


def test_log_store_append_and_list(tmp_path):
    store = AlertLogStore(_DBAdapter(str(tmp_path / "log.db")))
    models.AlertLog = SimpleNamespace
    stores.AlertLog = SimpleNamespace
    entry = SimpleNamespace(
        id="1",
        alert_id="a",
        phase="CONFIG",
        level="INFO",
        message="m",
        payload={"x": 1},
        timestamp=datetime.utcnow(),
    )
    store.append(entry)
    logs = store.list("a")
    assert len(logs) == 1
    assert logs[0].message == "m"
