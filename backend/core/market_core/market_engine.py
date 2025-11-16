from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Any

from backend.models.price_alert import PriceAlert
from backend.models.price_alert_event import PriceAlertEvent


STATE_OK = "OK"
STATE_WARN = "WARN"
STATE_BREACH = "BREACH"
STATE_DISARMED = "DISARMED"


def _threshold(alert: PriceAlert) -> float:
    return alert.effective_threshold_value or alert.base_threshold_value or 0.0


def _compute_moves(alert: PriceAlert, price: float) -> (float, float):
    anchor = alert.current_anchor_price
    if anchor is None or anchor == 0:
        return 0.0, 0.0
    move_abs = price - anchor
    move_pct = (move_abs / anchor) * 100.0
    return move_abs, move_pct


def _direction_ok(alert: PriceAlert, move_abs: float) -> bool:
    d = (alert.direction or "both").lower()
    if d in ("both", "above", "below"):
        return True
    if d == "up":
        return move_abs > 0
    if d == "down":
        return move_abs < 0
    return True


def _eval_state(alert: PriceAlert, price: float, move_abs: float, move_pct: float) -> (str, float, str):
    """
    Returns (state, proximity, threshold_desc).
    """
    thr = _threshold(alert)
    rule = (alert.rule_type or "move_pct").lower()
    direction = (alert.direction or "both").lower()

    metric = 0.0
    threshold_desc = ""

    if rule == "move_abs":
        metric = abs(move_abs)
        threshold_desc = f"${thr:.2f} move"
        if not _direction_ok(alert, move_abs):
            metric = 0.0
    elif rule == "move_pct":
        metric = abs(move_pct)
        threshold_desc = f"{thr:.2f}% move"
        if not _direction_ok(alert, move_abs):
            metric = 0.0
    else:  # price_target
        metric = price
        if direction in ("above", "up"):
            threshold_desc = f"price ≥ {thr:.2f}"
        elif direction in ("below", "down"):
            threshold_desc = f"price ≤ {thr:.2f}"
        else:
            threshold_desc = f"price crosses {thr:.2f}"

    proximity = 0.0
    if rule in ("move_abs", "move_pct") and thr > 0:
        proximity = max(0.0, min(metric / thr, 1.0))
    elif rule == "price_target" and thr > 0:
        if direction in ("above", "up"):
            proximity = max(0.0, min(price / thr, 1.0))
        elif direction in ("below", "down"):
            proximity = max(0.0, min(1.0, 1.0 - (price - thr) / max(thr, 1.0)))
        else:
            proximity = 1.0 if abs(price - thr) == 0 else max(
                0.0, min(1.0, 1.0 - abs(price - thr) / thr)
            )

    breached = False
    if rule == "price_target":
        if direction in ("above", "up"):
            breached = price >= thr
        elif direction in ("below", "down"):
            breached = price <= thr
        else:
            breached = price >= thr or price <= thr
    else:
        breached = thr > 0 and metric >= thr

    if not alert.enabled:
        state = STATE_DISARMED
    elif breached and alert.armed:
        state = STATE_BREACH
    elif proximity >= 0.7:
        state = STATE_WARN
    else:
        state = STATE_OK

    return state, proximity, threshold_desc


def _handle_recurrence(alert: PriceAlert, price: float, now_iso: str) -> None:
    mode = (alert.recurrence_mode or "single").lower()
    if mode == "single":
        alert.armed = False
    elif mode in ("reset", "ladder"):
        alert.current_anchor_price = price
        alert.current_anchor_time = now_iso
        if alert.original_anchor_price is None:
            alert.original_anchor_price = price
            alert.original_anchor_time = now_iso


def evaluate_market_alerts(dl, prices: Dict[str, float]) -> Dict[str, Any]:
    """
    Core Market monitor evaluation.

    dl: DataLocker
    prices: { "BTC": 12345.0, "ETH": ..., "SPX": ... }

    Returns:
      { ok, source, result, statuses }
    """
    now_iso = datetime.utcnow().isoformat()

    alerts: List[PriceAlert] = dl.price_alerts.list_alerts()
    rows_for_console: List[Dict[str, Any]] = []
    statuses: List[Dict[str, Any]] = []

    for alert in alerts:
        if not alert.enabled:
            continue

        price = prices.get(alert.asset)
        if price is None:
            continue

        # seed anchors
        if alert.current_anchor_price is None:
            alert.current_anchor_price = price
            alert.current_anchor_time = now_iso
        if alert.original_anchor_price is None:
            alert.original_anchor_price = alert.current_anchor_price
            alert.original_anchor_time = alert.current_anchor_time

        move_abs, move_pct = _compute_moves(alert, price)
        prev_state = alert.last_state or STATE_OK

        state, proximity, threshold_desc = _eval_state(alert, price, move_abs, move_pct)

        alert.last_state = state
        alert.last_price = price
        alert.last_move_abs = move_abs
        alert.last_move_pct = move_pct
        alert.last_proximity_ratio = proximity
        alert.last_evaluated_at = now_iso

        if state == STATE_BREACH and alert.armed and alert.enabled:
            # fire + apply recurrence
            alert.last_triggered_at = now_iso
            alert.fired_count = (getattr(alert, "fired_count", 0) or 0) + 1  # type: ignore[attr-defined]
            _handle_recurrence(alert, price, now_iso)

        alert.updated_at = now_iso
        dl.price_alerts.save_alert(alert)

        # log interesting transitions
        if prev_state != state:
            ev = PriceAlertEvent(
                alert_id=alert.id,
                asset=alert.asset,
                event_type="breach" if state == STATE_BREACH else "warn",
                state_after=state,
                price_at_event=price,
                anchor_at_event=alert.current_anchor_price,
                movement_value=move_abs,
                movement_percent=move_pct,
                threshold_value=_threshold(alert),
                rule_type=alert.rule_type,
                direction=alert.direction,
                recurrence_mode=alert.recurrence_mode,
                source="market_core",
            )
            dl.price_alert_events.record_event(ev)

        rows_for_console.append(
            {
                "asset": alert.asset,
                "label": alert.label or f"{alert.asset} alert",
                "price": price,
                "anchor_price": alert.current_anchor_price,
                "anchor_time": alert.current_anchor_time,
                "move_abs": move_abs,
                "move_pct": move_pct,
                "threshold_desc": threshold_desc,
                "proximity": proximity,
                "state": state,
            }
        )

        # monitor status row for dl_monitors / XCom
        value_metric = move_pct if (alert.rule_type or "").lower() == "move_pct" else move_abs
        meta = {
            "asset": alert.asset,
            "price": price,
            # anchor / entry info
            "anchor_price": alert.current_anchor_price,
            "anchor_time": alert.current_anchor_time,
            "original_anchor_price": alert.original_anchor_price,
            "original_anchor_time": alert.original_anchor_time,
            # movement metrics
            "move_abs": move_abs,
            "move_pct": move_pct,
            # threshold / rule metadata
            "threshold_desc": threshold_desc,
            "proximity": proximity,
            "rule_type": alert.rule_type,
            "direction": alert.direction,
            "recurrence_mode": alert.recurrence_mode,
        }

        statuses.append(
            {
                "monitor": "market",
                "label": alert.label or f"{alert.asset} move",
                "asset": alert.asset,
                "value": value_metric,
                "thr_value": _threshold(alert),
                "thr_op": ">=",
                "state": state,
                "source": "market_core",
                "meta": meta,
            }
        )

    return {
        "ok": True,
        "source": "market_core",
        "result": {"rows": rows_for_console},
        "statuses": statuses,
    }
