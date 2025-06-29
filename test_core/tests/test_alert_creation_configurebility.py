from datetime import datetime

from alert_core.infrastructure.stores import AlertStore, _DBAdapter
import alert_core.infrastructure.stores as stores
from data.alert import Condition, NotificationType, AlertLevel
from types import SimpleNamespace


def test_store_create_and_list(tmp_path):
    store = AlertStore(_DBAdapter(str(tmp_path / "alerts.db")))
    stores.Alert = SimpleNamespace
    alert = SimpleNamespace(
        id="1",
        description="a",
        alert_class="c",
        alert_type="t",
        trigger_value=1.0,
        evaluated_value=None,
        level=AlertLevel.NORMAL,
        position_reference_id=None,
        condition=Condition.ABOVE,
        notification_type=NotificationType.SMS,
        created_at=datetime.utcnow(),
    )
    store.create(alert)
    listed = store.list_active()
    assert len(listed) == 1
    assert listed[0].id == "1"
