import asyncio
from datetime import datetime

from alert_core.services.enrichment import AlertEnrichmentService
from alert_core.services.evaluation import AlertEvaluationService
from alert_core.domain.models import AlertLevel
from data.alert import Condition, NotificationType
from types import SimpleNamespace


async def run_pipeline(count: int = 10):
    enricher = AlertEnrichmentService()
    evaluator = AlertEvaluationService()
    alerts = [
        SimpleNamespace(
            id=str(i),
            description="d",
            alert_class="c",
            alert_type="t",
            trigger_value=float(i),
            evaluated_value=None,
            level=AlertLevel.NORMAL,
            condition=Condition.ABOVE,
            notification_type=NotificationType.SMS,
            created_at=datetime.utcnow(),
        )
        for i in range(count)
    ]
    enriched = await enricher.enrich_all(alerts)
    evaluated = [evaluator.evaluate(a) for a in enriched]
    return evaluated


def test_pipeline_runs():
    results = asyncio.run(run_pipeline(5))
    assert len(results) == 5
    assert all(r.level == AlertLevel.HIGH for r in results)
