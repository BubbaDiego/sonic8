from __future__ import annotations

from typing import Iterable, List, Any

#from data import Alert


class AlertEnrichmentService:
    """Add evaluated values to alerts."""

    def __init__(self, db=None) -> None:
        self.db = db


    async def enrich(self, alert: dict) -> dict:
        """Populate ``evaluated_value`` using ``trigger_value``.

        The test suite replaces the ``Alert`` model with ``types.SimpleNamespace``
        objects to avoid heavy dependencies.  During normal operation the model
        is a ``pydantic`` ``BaseModel`` instance which exposes attributes rather
        than dictionary-style item access.  To support both representations this
        method checks the type of ``alert`` and assigns the field accordingly.
        """

        if isinstance(alert, dict):
            alert["evaluated_value"] = alert.get("trigger_value")
        else:
            alert.evaluated_value = getattr(alert, "trigger_value")

        return alert

    async def enrich_all(self, alerts: Iterable[Any]) -> List[Any]:
        """Enrich a sequence of alerts preserving their original order."""
        return [await self.enrich(a) for a in alerts]
