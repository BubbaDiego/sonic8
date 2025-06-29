import os
import sys
import asyncio
from datetime import datetime

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from alert_core import AlertCore
from alert_core.domain.models import Alert, AlertLevel
from data.alert import Condition, NotificationType


@pytest.mark.asyncio
async def test_enrich_all_alerts_returns_enriched():
    core = AlertCore()
    alert = Alert(
        id="a1",
        description="d",
        alert_class="Test",
        alert_type="price",
        trigger_value=5.0,
        evaluated_value=None,
        condition=Condition.ABOVE,
        notification_type=NotificationType.SMS,
        created_at=datetime.utcnow(),
    )
    await core.create_alert(alert)

    enriched = await core.enrich_all_alerts()
    assert len(enriched) == 1
    assert enriched[0].evaluated_value == 5.0
