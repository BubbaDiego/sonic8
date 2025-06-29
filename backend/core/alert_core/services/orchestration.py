from __future__ import annotations

from datetime import datetime
from typing import List

from ..domain.models import Alert, AlertLog
from ..infrastructure.stores import AlertStore, AlertLogStore
from ..infrastructure.notifiers import default_router
from .enrichment import AlertEnrichmentService
from .evaluation import AlertEvaluationService


def _make_log(model_cls, **fields):
    """Instantiate ``model_cls`` with ``fields`` even when ``__init__`` is missing."""
    try:
        return model_cls(**fields)
    except TypeError:
        obj = model_cls()
        for k, v in fields.items():
            setattr(obj, k, v)
        return obj


class AlertOrchestrator:
    """High level facade for creating and processing alerts."""

    def __init__(self, store: AlertStore | None = None) -> None:
        self.store = store or AlertStore()
        self.log_store = AlertLogStore(self.store.db)
        self.enricher = AlertEnrichmentService(self.store.db)
        self.evaluator = AlertEvaluationService()
        self.notifiers = default_router

    async def create_alert(self, alert: Alert) -> bool:
        self.store.create(alert)
        return True

    async def enrich_all_alerts(self) -> list[Alert]:
        """Enrich all active alerts with latest data (see FULL_SPEC)."""
        alerts = self.store.list_active()
        if not alerts:
            return []
        enriched = await self.enricher.enrich_all(alerts)
        return enriched

    async def process_alerts(self) -> List[Alert]:
        alerts = self.store.list_active()
        enriched = await self.enricher.enrich_all(alerts)
        for a in enriched:
            self.log_store.append(
                _make_log(
                    AlertLog,
                    id=str(datetime.utcnow().timestamp()),
                    alert_id=a.id,
                    phase="ENRICH",
                    level="INFO",
                    message="enriched",
                    payload={"value": a.evaluated_value},
                    timestamp=datetime.utcnow(),
                )
            )
        results: List[Alert] = []
        for alert in enriched:
            evaluated = self.evaluator.evaluate(alert)

            if hasattr(self.notifiers, "route"):
                targets = self.notifiers.route(evaluated)
            else:
                targets = self.notifiers
            for notifier in targets:
                notifier.send(evaluated)

            self.log_store.append(
                _make_log(
                    AlertLog,
                    id=str(datetime.utcnow().timestamp()),
                    alert_id=evaluated.id,
                    phase="EVAL",
                    level="INFO",
                    message="evaluated",
                    payload={
                        "level": evaluated.level.value,
                        "value": evaluated.evaluated_value,
                    },
                    timestamp=datetime.utcnow(),
                )
            )
            for notifier in targets:
                success = notifier.send(evaluated)
                self.log_store.append(
                    _make_log(
                        AlertLog,
                        id=str(datetime.utcnow().timestamp()),
                        alert_id=evaluated.id,
                        phase="NOTIFY",
                        level="INFO" if success else "ERROR",
                        message="sent" if success else "failed",
                        payload={"notifier": notifier.__class__.__name__},
                        timestamp=datetime.utcnow(),
                    )
                )

            self.store.update_level_value(
                evaluated.id,
                evaluated.level.value,
                evaluated.evaluated_value or 0.0,
            )
            results.append(evaluated)
        return results
