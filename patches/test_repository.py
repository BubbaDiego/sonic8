
import pytest
from sqlalchemy.exc import IntegrityError
from alert_v2.models import (
    AlertConfig, Condition, NotificationType, AlertLevel, AlertState, Threshold
)
from datetime import datetime

def _sample_cfg():
    return AlertConfig(
        id="demo",
        alert_type="PriceThreshold",
        alert_class="Position",
        trigger_value=42_000,
        condition=Condition.ABOVE,
        notification_type=NotificationType.SMS,
    )

def test_add_and_get_config(repo):
    cfg = _sample_cfg()
    repo.add_config(cfg)
    loaded = repo.get_config(cfg.id)
    assert loaded == cfg

def test_state_auto_created(repo):
    cfg = _sample_cfg()
    repo.add_config(cfg)
    states = repo.active_states()
    assert len(states) == 1
    st = states[0]
    assert st.alert_id == cfg.id
    assert st.level == AlertLevel.NORMAL

def test_save_state(repo):
    cfg = _sample_cfg()
    repo.add_config(cfg)
    now = datetime.utcnow()
    repo.save_state(AlertState(
        alert_id=cfg.id,
        evaluated_value=42042,
        level=AlertLevel.HIGH,
        last_triggered=now,
    ))
    state = repo.active_states()[0]
    assert state.level == AlertLevel.HIGH
    assert state.last_triggered == now

def test_duplicate_config(repo):
    cfg = _sample_cfg()
    repo.add_config(cfg)
    with pytest.raises(IntegrityError):
        repo.add_config(cfg)

def test_threshold_crud(repo):
    th = Threshold(
        id="th1",
        alert_type="PriceThreshold",
        alert_class="Position",
        metric_key="mark_price",
        condition=Condition.ABOVE,
        low=100,
        medium=200,
        high=300,
    )
    repo.add_threshold(th)
    row = repo.thresholds_for("PriceThreshold", "Position", Condition.ABOVE)
    assert row == th

def test_log(repo):
    from alert_v2.models import AlertLog
    repo.log(AlertLog(id="log1", alert_id=None, phase="TEST", level="INFO", message="hello"))
    # ensures commit didn't raise
