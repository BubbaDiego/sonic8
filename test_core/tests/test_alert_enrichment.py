import asyncio
from datetime import datetime

import pytest

from alert_core.services.enrichment import AlertEnrichmentService
from data.alert import Condition, NotificationType, AlertLevel
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_enrich_sets_evaluated_value():
    service = AlertEnrichmentService()
    alert = SimpleNamespace(
        id="a1",
        description="d",
        alert_class="Test",
        alert_type="price",
        trigger_value=10.0,
        evaluated_value=None,
        level=AlertLevel.NORMAL,
        condition=Condition.ABOVE,
        notification_type=NotificationType.SMS,
        created_at=datetime.utcnow(),
    )
    result = await service.enrich(alert)
    assert result.evaluated_value == 10.0
    assert result.level == AlertLevel.NORMAL


@pytest.mark.asyncio
async def test_enrich_all_preserves_order():
    service = AlertEnrichmentService()
    alerts = [
        SimpleNamespace(
            id=str(i),
            description="d",
            alert_class="T",
            alert_type="t",
            trigger_value=float(i),
            evaluated_value=None,
            level=AlertLevel.NORMAL,
            condition=Condition.ABOVE,
            notification_type=NotificationType.SMS,
            created_at=datetime.utcnow(),
        )
        for i in range(5)
    ]
    results = await service.enrich_all(alerts)
    assert [a.id for a in results] == [str(i) for i in range(5)]
    assert all(r.evaluated_value == float(r.id) for r in results)
