from __future__ import annotations

from ..domain.models import Alert, AlertLevel, Condition


class AlertEvaluationService:
    """Compute alert level from evaluated value and trigger."""

    def evaluate(self, alert: Alert) -> Alert:
        value = alert.evaluated_value
        if value is None:
            alert.level = AlertLevel.NORMAL
            return alert

        if alert.condition == Condition.ABOVE:
            alert.level = (
                AlertLevel.HIGH if value >= alert.trigger_value else AlertLevel.NORMAL
            )
        elif alert.condition == Condition.BELOW:
            alert.level = (
                AlertLevel.HIGH if value <= alert.trigger_value else AlertLevel.NORMAL
            )
        else:
            alert.level = AlertLevel.NORMAL
        return alert
