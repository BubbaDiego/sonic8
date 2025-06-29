from alert_core.services.evaluation import AlertEvaluationService
from data.alert import Condition, AlertLevel
from types import SimpleNamespace
from datetime import datetime


def test_evaluation_levels():
    svc = AlertEvaluationService()
    alert = SimpleNamespace(
        id="a",
        description="d",
        alert_class="c",
        alert_type="t",
        trigger_value=5.0,
        evaluated_value=10.0,
        level=AlertLevel.NORMAL,
        condition=Condition.ABOVE,
        created_at=datetime.utcnow(),
    )
    evaluated = svc.evaluate(alert)
    assert evaluated.level == AlertLevel.HIGH
    alert.evaluated_value = 1.0
    evaluated = svc.evaluate(alert)
    assert evaluated.level == AlertLevel.NORMAL
