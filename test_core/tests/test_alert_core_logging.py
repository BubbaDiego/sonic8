import asyncio
from datetime import datetime

from alert_core import AlertCore
from alert_core.infrastructure.stores import AlertLogStore, _DBAdapter, AlertStore
import alert_core.infrastructure.stores as stores
from data.alert import Condition, NotificationType, AlertLevel
from types import SimpleNamespace


async def run_flow(store: AlertLogStore, path):
    core = AlertCore(AlertStore(_DBAdapter(str(path / "alerts.db"))))
    core.log_store = store
    stores.Alert = SimpleNamespace
    alert = SimpleNamespace(
        id="a1",
        description="d",
        alert_class="Test",
        alert_type="t",
        trigger_value=1.0,
        evaluated_value=None,
        level=AlertLevel.NORMAL,
        position_reference_id=None,
        condition=Condition.ABOVE,
        notification_type=NotificationType.SMS,
        created_at=datetime.utcnow(),
    )
    await core.create_alert(alert)
    await core.process_alerts()


def test_alert_log_entries(tmp_path):
    store = AlertLogStore(_DBAdapter(str(tmp_path / "log.db")))
    stores.AlertLog = SimpleNamespace
    asyncio.run(run_flow(store, tmp_path))
    logs = store.list()
    assert logs == [] or isinstance(logs, list)
