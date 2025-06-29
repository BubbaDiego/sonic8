import asyncio
import pytest
from datetime import datetime

from alert_core.services.enrichment import AlertEnrichmentService
from data.alert import Condition, NotificationType
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_bulk_enrich_preserves_values():
    service = AlertEnrichmentService()
    alerts = [
        SimpleNamespace(
            id=f"a{i}",
            description="d",
            alert_class="c",
            alert_type="t",
            trigger_value=float(i),
            evaluated_value=None,
            level=None,
            condition=Condition.BELOW,
            notification_type=NotificationType.SMS,
            created_at=datetime.utcnow(),
        )
        for i in range(20)
    ]
    results = []
    for a in alerts:
        results.append(await service.enrich(a))

    assert [r.evaluated_value for r in results] == [float(i) for i in range(20)]
