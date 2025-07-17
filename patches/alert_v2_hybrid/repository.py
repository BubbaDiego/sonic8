
from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from datetime import datetime

from .db import get_session
from .models import (
    AlertConfig, AlertState, Threshold, AlertEvent,
    AlertConfigTbl, AlertStateTbl, ThresholdTbl, AlertEventTbl, AlertLevel
)

class AlertRepo:
    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()

    # ---------------- Schema ----------------
    def ensure_schema(self):
        from .models import Base
        Base.metadata.create_all(bind=self.session.get_bind())

    # ---------------- Config ----------------
    def add_config(self, cfg: AlertConfig):
        row = AlertConfigTbl(**cfg.model_dump())
        state_row = AlertStateTbl(alert_id=cfg.id)
        self.session.add_all([row, state_row])
        self.session.commit()

    def get_config(self, alert_id: str) -> Optional[AlertConfig]:
        row = self.session.get(AlertConfigTbl, alert_id)
        return AlertConfig.model_validate(row.__dict__) if row else None

    def iter_alerts_with_state(self):
        q = (
            select(AlertConfigTbl, AlertStateTbl)
            .join(AlertStateTbl, AlertConfigTbl.id == AlertStateTbl.alert_id)
        )
        for cfg_row, st_row in self.session.execute(q).all():
            yield (
                AlertConfig.model_validate(cfg_row.__dict__),
                AlertState.model_validate(st_row.__dict__),
            )

    # ---------------- State ----------------
    def save_state(self, state: AlertState):
        row = self.session.get(AlertStateTbl, state.alert_id)
        if row is None:
            row = AlertStateTbl(**state.model_dump())
            self.session.add(row)
        else:
            for k, v in state.model_dump().items():
                setattr(row, k, v)
        self.session.commit()

    # ---------------- Thresholds ----------------
    def add_threshold(self, th: Threshold):
        row = ThresholdTbl(**th.model_dump())
        self.session.add(row)
        self.session.commit()

    def thresholds_for(self, alert_type: str, alert_class: str, condition):
        q = (
            select(ThresholdTbl)
            .where(
                ThresholdTbl.alert_type == alert_type,
                ThresholdTbl.alert_class == alert_class,
                ThresholdTbl.condition == condition,
                ThresholdTbl.enabled == True,  # noqa
            )
            .order_by(ThresholdTbl.last_modified.desc())
            .limit(1)
        )
        row = self.session.execute(q).scalars().first()
        return Threshold.model_validate(row.__dict__) if row else None

    # ---------------- Events ----------------
    def add_event(self, ev: AlertEvent):
        row = AlertEventTbl(**ev.model_dump())
        self.session.add(row)
        self.session.commit()

    def last_events(self, limit: int = 100, alert_id: Optional[str] = None) -> List[AlertEvent]:
        q = select(AlertEventTbl).order_by(AlertEventTbl.created_at.desc()).limit(limit)
        if alert_id:
            q = q.where(AlertEventTbl.alert_id == alert_id)
        rows = self.session.execute(q).scalars().all()
        return [AlertEvent.model_validate(r.__dict__) for r in rows]
