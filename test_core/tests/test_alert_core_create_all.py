import asyncio
from datetime import datetime

from alert_core import AlertCore
from alert_core.domain.models import Condition, NotificationType, AlertLevel
from alert_core.infrastructure.stores import AlertStore, _DBAdapter
import alert_core.infrastructure.stores as stores
from types import SimpleNamespace
from types import SimpleNamespace


def test_create_alert_runs(tmp_path):
    core = AlertCore(AlertStore(_DBAdapter(str(tmp_path / "alerts.db"))))
    stores.Alert = SimpleNamespace
    alert = SimpleNamespace(
        id="1",
        description="d",
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
    asyncio.run(core.create_alert(alert))
