
from __future__ import annotations
from typing import Tuple, Optional
from uuid import uuid4
from datetime import datetime

from ..models import AlertConfig, AlertState, Threshold, AlertLevel, AlertEvent

def evaluate(cfg: AlertConfig, state: AlertState, metric: float, threshold: Threshold) -> Tuple[AlertState, Optional[AlertEvent]]:
    """Pure function that returns a possibly-updated state and an optional event."""
    # determine level
    if threshold.condition == cfg.condition == threshold.condition:
        if metric >= threshold.high:
            level = AlertLevel.HIGH
        elif metric >= threshold.medium:
            level = AlertLevel.MEDIUM
        elif metric >= threshold.low:
            level = AlertLevel.LOW
        else:
            level = AlertLevel.NORMAL
    else:
        # BELOW logic
        if metric <= threshold.high:
            level = AlertLevel.HIGH
        elif metric <= threshold.medium:
            level = AlertLevel.MEDIUM
        elif metric <= threshold.low:
            level = AlertLevel.LOW
        else:
            level = AlertLevel.NORMAL

    event = None
    if level != state.last_level:
        ev_id = f"ev-{uuid4()}"
        event = AlertEvent(
            id=ev_id,
            alert_id=cfg.id,
            level=level,
            metric_value=metric,
            message=f"Level changed {state.last_level} → {level}",
            created_at=datetime.utcnow(),
        )
        # update state
        state.last_event_id = ev_id
        state.last_level = level
        state.last_value = metric
    else:
        # still update last_value
        state.last_value = metric

    return state, event
