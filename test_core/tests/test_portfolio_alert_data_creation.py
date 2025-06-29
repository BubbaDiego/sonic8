import asyncio
from datetime import datetime

import pytest

from alert_core.services.enrichment import AlertEnrichmentService
from data.alert import Condition, NotificationType
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_multiple_alert_enrichment():
    service = AlertEnrichmentService()
    alerts = [
        SimpleNamespace(
            id=f"p{i}",
            description="d",
            alert_class="Portfolio",
            alert_type="t",
            trigger_value=float(i),
            evaluated_value=None,
            level=None,
            condition=Condition.ABOVE,
            notification_type=NotificationType.SMS,
            created_at=datetime.utcnow(),
        )
        for i in range(3)
    ]
    enriched = await service.enrich_all(alerts)
    assert [a.evaluated_value for a in enriched] == [0.0, 1.0, 2.0]
