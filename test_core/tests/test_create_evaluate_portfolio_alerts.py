import asyncio
from datetime import datetime

from alert_core import AlertCore
from alert_core.domain.models import AlertLevel
from data.alert import Condition, NotificationType
from alert_core.infrastructure.stores import AlertStore, _DBAdapter
import alert_core.infrastructure.stores as stores
from types import SimpleNamespace


async def run_flow(tmp_path):
    core = AlertCore(AlertStore(_DBAdapter(str(tmp_path / "alerts.db"))))
    stores.Alert = SimpleNamespace
    alert = SimpleNamespace(
        id="p1",
        description="port",
        alert_class="Portfolio",
        alert_type="t",
        trigger_value=5.0,
        evaluated_value=None,
        level=AlertLevel.NORMAL,
        position_reference_id=None,
        condition=Condition.ABOVE,
        notification_type=NotificationType.SMS,
        created_at=datetime.utcnow(),
    )
    await core.create_alert(alert)
    processed = await core.process_alerts()
    return processed[0]


def test_create_and_evaluate_portfolio_alert(tmp_path):
    result = asyncio.run(run_flow(tmp_path))
    assert result.level == AlertLevel.HIGH
