
from backend.alert_v2.models import AlertConfig, AlertState, Condition, Threshold
from backend.alert_v2.services.evaluation import evaluate, AlertLevel

def test_evaluate_level_change():
    cfg = AlertConfig(
        id="cfg1",
        alert_type="Price",
        alert_class="Position",
        trigger_value=100,
        condition=Condition.ABOVE,
    )
    state = AlertState(alert_id=cfg.id)
    threshold = Threshold(
        id="th1",
        alert_type="Price",
        alert_class="Position",
        metric_key="mark_price",
        condition=Condition.ABOVE,
        low=50,
        medium=75,
        high=100,
    )
    new_state, event = evaluate(cfg, state, metric=120, threshold=threshold)
    assert new_state.last_level == AlertLevel.HIGH
    assert event is not None
