import asyncio
from datetime import datetime

import pytest
from unittest.mock import MagicMock

from alert_core.services.enrichment import AlertEnrichmentService
from data.alert import Condition, NotificationType
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_enrich_returns_trigger_value():
    service = AlertEnrichmentService(MagicMock())
    alert = SimpleNamespace(
        id="1",
        description="p",
        alert_class="Portfolio",
        alert_type="t",
        trigger_value=20.0,
        evaluated_value=None,
        level=None,
        condition=Condition.ABOVE,
        notification_type=NotificationType.SMS,
        created_at=datetime.utcnow(),
    )
    result = await service.enrich(alert)
    assert result.evaluated_value == 20.0
