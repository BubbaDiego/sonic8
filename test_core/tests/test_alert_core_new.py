import asyncio
from datetime import datetime

from alert_core import AlertCore
from data.alert import Condition, NotificationType, Alert, AlertLevel


class DummyNotifier:
    def __init__(self):
        self.sent = []

    def send(self, alert):
        self.sent.append(alert)
        return True


async def run_flow():
    core = AlertCore()
    dummy = DummyNotifier()
    core.notifiers = [dummy]
    alert = Alert(
        id="a1",
        description="test alert",
        alert_class="Test",
        alert_type="price",
        trigger_value=1.0,
        evaluated_value=None,
        condition=Condition.ABOVE,
        notification_type=NotificationType.SMS,
        created_at=datetime.utcnow(),
    )
    await core.create_alert(alert)
    results = await core.process_alerts()
    return results, dummy


def test_alert_processing():
    results, dummy = asyncio.run(run_flow())
    assert len(results) == 1
    alert = results[0]
    assert alert.level == AlertLevel.HIGH
    assert dummy.sent

