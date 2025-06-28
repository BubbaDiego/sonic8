import asyncio
from datetime import datetime
import pytest

from alert_core.services.enrichment import AlertEnrichmentService
from alert_core.domain.models import Condition, NotificationType
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_enrich_all_order():
    service = AlertEnrichmentService()
    alerts = [
        SimpleNamespace(id=str(i), description="d", alert_class="c", alert_type="t", trigger_value=float(i),
                        condition=Condition.ABOVE, notification_type=NotificationType.SMS, created_at=datetime.utcnow())
        for i in range(3)
    ]
    enriched = await service.enrich_all(alerts)
    assert [a.id for a in enriched] == ["0", "1", "2"]
