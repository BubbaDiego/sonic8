# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Iterable, Optional, Any, Tuple

from backend.models.price_alert import (
    PriceAlert,
    PriceAlertConfig,
    PriceAlertState,
    PriceAlertMode,
    PriceAlertDirection,
    PriceAlertRecurrence,
    PriceAlertStateEnum,
)
from backend.models.price_alert_event import (
    PriceAlertEvent,
    PriceAlertEventType,
)


@dataclass
class MarketAlertStatus:
    """
    Lightweight status row suitable for dl_monitors and console panels.
    The Sonic monitor runner can adapt this to its MonitorStatus schema.
    """

    alert_id: Optional[int]
    asset: str
    name: str
    state: PriceAlertStateEnum
    price: Optional[float]
    anchor_price: Optional[float]
    move_abs: Optional[float]
    move_pct: Optional[float]
    threshold_value: float
    mode: PriceAlertMode
    direction: PriceAlertDirection
    proximity_ratio: float
    recurrence: PriceAlertRecurrence
    last_evaluated_at: datetime


@dataclass
class MarketEvaluationResult:
    alerts: List[PriceAlert]
    events: List[PriceAlertEvent]
    statuses: List[MarketAlertStatus]


class MarketCore:
    """
    Pure Market Core evaluation engine.

    It doesn't know about DataLocker or the DB. You give it:

      • a list of PriceAlert objects
      • a mapping {asset_symbol: latest_price}

    and it returns updated alerts, a list of PriceAlertEvent rows to log,
    and status rows to feed into dl_monitors and the Market panel.
    """

    def __init__(
        self,
        alerts: Iterable[PriceAlert],
        prices_by_asset: Dict[str, float],
        *,
        now: Optional[datetime] = None,
    ) -> None:
        self._alerts = list(alerts)
        self._prices = prices_by_asset
        self._now = now or datetime.utcnow()

    # ───────────────────────── public API ─────────────────────────

    def evaluate(self) -> MarketEvaluationResult:
        updated_alerts: List[PriceAlert] = []
        events: List[PriceAlertEvent] = []
        statuses: List[MarketAlertStatus] = []

        for alert in self._alerts:
            updated, evts, status = self._evaluate_one(alert)
            updated_alerts.append(updated)
            events.extend(evts)
            if status is not None:
                statuses.append(status)

        return MarketEvaluationResult(
            alerts=updated_alerts,
            events=events,
            statuses=statuses,
        )

    # ───────────────────────── internals ─────────────────────────

    def _evaluate_one(
        self,
        alert: PriceAlert,
    ) -> Tuple[PriceAlert, List[PriceAlertEvent], Optional[MarketAlertStatus]]:
        cfg: PriceAlertConfig = alert.config
        st: PriceAlertState = alert.state
        now = self._now
        events: List[PriceAlertEvent] = []

        price = self._prices.get(cfg.asset)
        if price is None:
            # No price → bump timestamps but don't change state.
            new_state = st.copy(update={"last_evaluated_at": now})
            updated_alert = alert.copy_with(state_updates=new_state.dict())
            return updated_alert, events, None

        # Seed anchors if needed.
        original_anchor_price = st.original_anchor_price
        current_anchor_price = st.current_anchor_price

        if current_anchor_price is None:
            current_anchor_price = price
            st.current_anchor_price = current_anchor_price
            st.current_anchor_time = now

        if original_anchor_price is None:
            original_anchor_price = current_anchor_price
            st.original_anchor_price = original_anchor_price
            st.original_anchor_time = st.current_anchor_time or now

        move_abs: Optional[float] = None
        move_pct: Optional[float] = None
        distance_to_target: Optional[float] = None
        proximity_ratio: float = 0.0

        # Movement or target math
        if cfg.mode in (PriceAlertMode.MOVE_ABSOLUTE, PriceAlertMode.MOVE_PERCENT):
            move_abs = price - current_anchor_price
            if current_anchor_price:
                move_pct = (move_abs / current_anchor_price) * 100.0

            magnitude = abs(
                move_abs
                if cfg.mode == PriceAlertMode.MOVE_ABSOLUTE
                else (move_pct or 0.0)
            )
            threshold = cfg.threshold_value or 0.0
            proximity_ratio = 0.0 if threshold <= 0 else max(
                0.0, min(magnitude / threshold, 1.0)
            )
        else:
            # PRICE_TARGET
            target = cfg.threshold_value
            distance_to_target = abs(price - target)
            if target > 0:
                if cfg.direction in (PriceAlertDirection.ABOVE, PriceAlertDirection.UP):
                    if price >= target:
                        proximity_ratio = 1.0
                    else:
                        proximity_ratio = max(0.0, price / target)
                elif cfg.direction in (PriceAlertDirection.BELOW, PriceAlertDirection.DOWN):
                    if price <= target:
                        proximity_ratio = 1.0
                    else:
                        proximity_ratio = max(
                            0.0,
                            min(1.0, 1.0 - (price - target) / max(target, 1.0)),
                        )
                else:
                    proximity_ratio = max(
                        0.0, min(1.0, 1.0 - distance_to_target / target)
                    )
            else:
                proximity_ratio = 0.0

        # Is movement in the direction we care about?
        direction_ok = self._direction_matches(
            cfg, move_abs, move_pct, price, current_anchor_price
        )

        prev_state = st.last_state

        # Determine new state
        if not cfg.enabled:
            new_state_enum = PriceAlertStateEnum.DISARMED
        elif cfg.mode == PriceAlertMode.PRICE_TARGET:
            triggered = self._is_target_triggered(cfg, price)
            new_state_enum = (
                PriceAlertStateEnum.BREACH if triggered and st.armed else PriceAlertStateEnum.OK
            )
        else:
            # Movement rules
            if not direction_ok or cfg.threshold_value <= 0:
                new_state_enum = PriceAlertStateEnum.OK
            else:
                threshold = cfg.threshold_value
                magnitude = abs(
                    move_abs
                    if cfg.mode == PriceAlertMode.MOVE_ABSOLUTE
                    else (move_pct or 0.0)
                )
                ratio = 0.0 if threshold <= 0 else magnitude / threshold
                proximity_ratio = max(0.0, min(ratio, 1.0))
                if ratio >= 1.0 and st.armed:
                    new_state_enum = PriceAlertStateEnum.BREACH
                elif ratio >= 0.7:
                    new_state_enum = PriceAlertStateEnum.WARN
                else:
                    new_state_enum = PriceAlertStateEnum.OK

        st_dict: Dict[str, Any] = st.dict()
        st_dict.update(
            last_price=price,
            last_move_abs=move_abs,
            last_move_pct=move_pct,
            last_distance_to_target=distance_to_target,
            last_proximity_ratio=proximity_ratio,
            last_evaluated_at=now,
        )

        def record_event(ev_type: PriceAlertEventType) -> None:
            events.append(
                PriceAlertEvent(
                    alert_id=cfg.id,
                    asset=cfg.asset,
                    event_type=ev_type,
                    state_after=new_state_enum,
                    mode=cfg.mode,
                    direction=cfg.direction,
                    price=price,
                    anchor_price=current_anchor_price,
                    threshold_value=cfg.threshold_value,
                    movement_abs=move_abs,
                    movement_pct=move_pct,
                    distance_to_target=distance_to_target,
                    proximity_ratio=proximity_ratio,
                )
            )

        # Recurrence + BREACH handling
        if new_state_enum == PriceAlertStateEnum.BREACH and cfg.enabled and st.armed:
            st_dict["last_triggered_at"] = now
            st_dict["fired_count"] = st.fired_count + 1

            if cfg.recurrence == PriceAlertRecurrence.SINGLE:
                st_dict["armed"] = False
            elif cfg.recurrence == PriceAlertRecurrence.RESET:
                st_dict["current_anchor_price"] = price
                st_dict["current_anchor_time"] = now
            elif cfg.recurrence == PriceAlertRecurrence.LADDER and cfg.threshold_value > 0:
                step = cfg.threshold_value
                if cfg.mode == PriceAlertMode.MOVE_PERCENT:
                    if move_pct is not None and move_pct != 0:
                        factor = 1.0 + (step / 100.0) * (1 if move_pct > 0 else -1)
                    else:
                        factor = 1.0
                    st_dict["current_anchor_price"] = current_anchor_price * factor
                else:
                    sign = 1.0 if (move_abs or 0.0) >= 0 else -1.0
                    st_dict["current_anchor_price"] = current_anchor_price + sign * step
                st_dict["current_anchor_time"] = now

            record_event(PriceAlertEventType.BREACH)
        elif (
            new_state_enum == PriceAlertStateEnum.WARN
            and prev_state != PriceAlertStateEnum.WARN
        ):
            record_event(PriceAlertEventType.WARN)

        st_dict["last_state"] = new_state_enum
        new_state = PriceAlertState(**st_dict)
        updated_alert = PriceAlert(config=cfg, state=new_state)

        status = MarketAlertStatus(
            alert_id=cfg.id,
            asset=cfg.asset,
            name=cfg.name or f"{cfg.asset} alert",
            state=new_state_enum,
            price=price,
            anchor_price=new_state.current_anchor_price,
            move_abs=new_state.last_move_abs,
            move_pct=new_state.last_move_pct,
            threshold_value=cfg.threshold_value,
            mode=cfg.mode,
            direction=cfg.direction,
            proximity_ratio=new_state.last_proximity_ratio or 0.0,
            recurrence=cfg.recurrence,
            last_evaluated_at=new_state.last_evaluated_at or now,
        )

        return updated_alert, events, status

    # ───────────────────────── helpers ─────────────────────────

    @staticmethod
    def _direction_matches(
        cfg: PriceAlertConfig,
        move_abs: Optional[float],
        move_pct: Optional[float],
        price: float,
        anchor_price: float,
    ) -> bool:
        """Check whether the move is in the direction this rule cares about."""
        if cfg.mode == PriceAlertMode.PRICE_TARGET:
            return True  # handled separately

        delta = move_abs if cfg.mode == PriceAlertMode.MOVE_ABSOLUTE else (move_pct or 0.0)
        if delta is None:
            return False

        if cfg.direction == PriceAlertDirection.BOTH:
            return True
        if cfg.direction in (PriceAlertDirection.UP, PriceAlertDirection.ABOVE):
            return delta > 0
        if cfg.direction in (PriceAlertDirection.DOWN, PriceAlertDirection.BELOW):
            return delta < 0
        return True

    @staticmethod
    def _is_target_triggered(cfg: PriceAlertConfig, price: float) -> bool:
        """Check if a PRICE_TARGET alert is actually in breach."""
        target = cfg.threshold_value
        if cfg.direction in (PriceAlertDirection.ABOVE, PriceAlertDirection.UP):
            return price >= target
        if cfg.direction in (PriceAlertDirection.BELOW, PriceAlertDirection.DOWN):
            return price <= target
        # BOTH / default: any side crossing
        return price >= target or price <= target
