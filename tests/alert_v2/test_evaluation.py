
from backend.alert_v2.models import AlertConfig, AlertState, Condition, Threshold
from backend.alert_v2.services.evaluation import evaluate, AlertLevel

def test_evaluate_level_change_above():
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

    # no change -> no event
    new_state, event = evaluate(cfg, new_state, metric=110, threshold=threshold)
    assert new_state.last_level == AlertLevel.HIGH
    assert event is None


def test_evaluate_level_change_below():
    cfg = AlertConfig(
        id="cfg2",
        alert_type="Price",
        alert_class="Position",
        trigger_value=100,
        condition=Condition.BELOW,
    )
    state = AlertState(alert_id=cfg.id)
    threshold = Threshold(
        id="th2",
        alert_type="Price",
        alert_class="Position",
        metric_key="mark_price",
        condition=Condition.BELOW,
        low=90,
        medium=70,
        high=50,
    )

    state, event = evaluate(cfg, state, metric=40, threshold=threshold)
    assert state.last_level == AlertLevel.HIGH
    assert event is not None

    state, event = evaluate(cfg, state, metric=60, threshold=threshold)
    assert state.last_level == AlertLevel.MEDIUM
    assert event is not None

    state, event = evaluate(cfg, state, metric=65, threshold=threshold)
    assert state.last_level == AlertLevel.MEDIUM
    assert event is None
