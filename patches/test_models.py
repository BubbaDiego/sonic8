
import pytest
from pydantic import ValidationError
from alert_v2.models import AlertConfig, Condition, NotificationType

def test_alert_config_validation():
    cfg = AlertConfig(
        id="a1",
        alert_type="Price",
        alert_class="Position",
        trigger_value=100.5,
        condition=Condition.ABOVE,
        notification_type=NotificationType.EMAIL,
    )
    assert cfg.trigger_value == 100.5
    assert cfg.model_dump()["condition"] == "ABOVE"

def test_alert_config_negative_value():
    with pytest.raises(ValidationError):
        AlertConfig(
            id="bad",
            alert_type="Price",
            alert_class="Position",
            trigger_value=-1.0,
            condition=Condition.BELOW,
        )
