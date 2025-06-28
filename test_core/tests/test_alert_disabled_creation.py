from datetime import datetime

from alert_core.infrastructure.stores import AlertStore, _DBAdapter
import alert_core.infrastructure.stores as stores
from alert_core.domain.models import Condition, NotificationType, AlertLevel
from types import SimpleNamespace


def test_update_level_value(tmp_path):
    store = AlertStore(_DBAdapter(str(tmp_path / "alerts.db")))
    stores.Alert = SimpleNamespace
    alert = SimpleNamespace(
        id="x",
        description="d",
        alert_class="c",
        alert_type="t",
        trigger_value=1.0,
        evaluated_value=0.0,
        level=AlertLevel.NORMAL,
        position_reference_id=None,
        condition=Condition.ABOVE,
        notification_type=NotificationType.SMS,
        created_at=datetime.utcnow(),
    )
    store.create(alert)
    store.update_level_value("x", AlertLevel.HIGH.value, 2.0)
    updated = store.list_active()[0]
    assert updated.level == AlertLevel.HIGH
    assert updated.evaluated_value == 2.0
