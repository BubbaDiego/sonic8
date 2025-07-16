
"""Alert repository – single source of truth for configs, state, thresholds and logs."""
from __future__ import annotations
from typing import List, Optional

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from .models import (
    AlertConfig, AlertState, Threshold, AlertLog,
    AlertConfigTbl, AlertStateTbl, ThresholdTbl, AlertLogTbl
)
from .db import get_session
from uuid import uuid4
from datetime import datetime

class AlertRepo:
    """Thin CRUD wrapper around SQLAlchemy Session.

    Designed to be injected via FastAPI Depends.
    """

    def __init__(self, session: Optional[Session] = None):
        self.session = session or get_session()

    # ------------------------
    # Config
    # ------------------------
    def add_config(self, cfg: AlertConfig) -> None:
        row = AlertConfigTbl(**cfg.model_dump())
        # create state placeholder too
        state_row = AlertStateTbl(alert_id=cfg.id)
        self.session.add_all([row, state_row])
        self.session.commit()

    def get_config(self, alert_id: str) -> Optional[AlertConfig]:
        row = self.session.get(AlertConfigTbl, alert_id)
        return AlertConfig.model_validate(row.__dict__) if row else None

    # ------------------------
    # State
    # ------------------------
    def save_state(self, state: AlertState) -> None:
        row = self.session.get(AlertStateTbl, state.alert_id)
        if row is None:
            row = AlertStateTbl(**state.model_dump())
            self.session.add(row)
        else:
            for k, v in state.model_dump().items():
                setattr(row, k, v)
        self.session.commit()

    def active_states(self) -> List[AlertState]:
        q = select(AlertStateTbl).options(selectinload(AlertStateTbl.config))
        rows = self.session.execute(q).scalars().all()
        return [AlertState.model_validate(r.__dict__) for r in rows]

    # ------------------------
    # Thresholds
    # ------------------------
    def add_threshold(self, th: Threshold) -> None:
        row = ThresholdTbl(**th.model_dump())
        self.session.add(row)
        self.session.commit()

    def thresholds_for(self, alert_type: str, alert_class: str, condition: str):
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

    # ------------------------
    # Logs
    # ------------------------
    def log(self, entry: AlertLog) -> None:
        row = AlertLogTbl(**entry.model_dump())
        self.session.add(row)
        self.session.commit()

    # ------------------------
    # Utility
    # ------------------------
    def ensure_schema(self) -> None:
        from .models import Base
        Base.metadata.create_all(bind=self.session.get_bind())
