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


def _eval_state(
    alert: PriceAlert, price: float, move_abs: float, move_pct: float
) -> (str, float, str, float | None, float):
    """
    Returns (state, proximity, threshold_desc, metric, threshold_value).
    """

    thr = _threshold(alert)
    rule = (alert.rule_type or "move_pct").lower()
    direction = (alert.direction or "both").lower()
    direction = "up" if direction == "above" else "down" if direction == "below" else direction

    warn_ratio = 0.7
    threshold_desc = ""
    proximity = 0.0
    metric: float | None = None
    threshold_value = 0.0

    if rule in ("move_abs", "move_pct"):
        threshold_value = abs(thr)
        raw_value = move_pct if rule == "move_pct" else move_abs

        if raw_value is not None:
            if direction == "up":
                metric = max(raw_value, 0.0)
            elif direction == "down":
                metric = max(-raw_value, 0.0)
            else:
                metric = abs(raw_value)

        if rule == "move_pct":
            threshold_desc = f"{threshold_value:.2f}% move"
        else:
            threshold_desc = f"${threshold_value:.2f} move"

        if metric is not None and threshold_value > 0:
            ratio = metric / threshold_value
        else:
            ratio = 0.0

        proximity = max(0.0, min(ratio, 1.0))

        if not alert.enabled:
            state = STATE_DISARMED
        elif threshold_value <= 0 or metric is None:
            state = STATE_OK
        elif ratio >= 1.0:
            state = STATE_BREACH
        elif ratio >= warn_ratio:
            state = STATE_WARN
        else:
            state = STATE_OK

    else:  # price_target
        threshold_value = thr
        metric = price
        if direction in ("above", "up"):
            threshold_desc = f"price ≥ {thr:.2f}"
        elif direction in ("below", "down"):
            threshold_desc = f"price ≤ {thr:.2f}"
        else:
            threshold_desc = f"price crosses {thr:.2f}"

        if thr > 0:
            if direction in ("above", "up"):
                proximity = max(0.0, min(price / thr, 1.0))
            elif direction in ("below", "down"):
                proximity = max(0.0, min(1.0, 1.0 - (price - thr) / max(thr, 1.0)))
            else:
                proximity = 1.0 if abs(price - thr) == 0 else max(
                    0.0, min(1.0, 1.0 - abs(price - thr) / thr)
                )

        breached = False
        if direction in ("above", "up"):
            breached = price >= thr
        elif direction in ("below", "down"):
            breached = price <= thr
        else:
            breached = price >= thr or price <= thr

        if not alert.enabled:
            state = STATE_DISARMED
        elif breached and alert.armed:
            state = STATE_BREACH
        elif proximity >= warn_ratio:
            state = STATE_WARN
        else:
            state = STATE_OK

    return state, proximity, threshold_desc, metric, threshold_value


def _handle_recurrence(alert: PriceAlert, price: float, now_iso: str) -> bool:
    mode = (alert.recurrence_mode or "single").lower()
    anchor_updated = False
    if mode == "single":
        alert.armed = False
    elif mode == "reset":
        alert.current_anchor_price = price
        alert.current_anchor_time = now_iso
        anchor_updated = True
        if alert.original_anchor_price is None:
            alert.original_anchor_price = price
            alert.original_anchor_time = now_iso
    elif mode == "ladder":
        if alert.original_anchor_price is None:
            alert.original_anchor_price = alert.current_anchor_price or price
            alert.original_anchor_time = alert.current_anchor_time or now_iso
    return anchor_updated


def evaluate_market_alerts(dl, prices: Dict[str, float]) -> Dict[str, Any]:
    """
    Core Market monitor evaluation.

    dl: DataLocker
    prices: { "BTC": 12345.0, "ETH": ..., "SPX": ... }

    Returns:
      { ok, source, result, statuses }
    """
    now_dt = datetime.utcnow()
    now_iso = now_dt.isoformat()
    now_ts = now_dt.timestamp()
    window_seconds = 600

    alerts: List[PriceAlert] = dl.price_alerts.list_alerts()
    rows_for_console: List[Dict[str, Any]] = []
    statuses: List[Dict[str, Any]] = []

    for alert in alerts:
        if not alert.enabled:
            continue

        price = prices.get(alert.asset)
        if price is None:
            continue

        meta = dict(getattr(alert, "metadata", None) or {})
        recent_alert_ts = []
        try:
            for ts in meta.get("recent_alert_ts", []) or []:
                try:
                    ts_f = float(ts)
                except (TypeError, ValueError):
                    continue
                if now_ts - ts_f <= window_seconds:
                    recent_alert_ts.append(ts_f)
        except Exception:
            recent_alert_ts = []

        anchor_set_now = False
        # seed anchors
        if alert.current_anchor_price is None:
            alert.current_anchor_price = price
            alert.current_anchor_time = now_iso
            anchor_set_now = True
        if alert.original_anchor_price is None:
            alert.original_anchor_price = alert.current_anchor_price
            alert.original_anchor_time = alert.current_anchor_time

        move_abs, move_pct = _compute_moves(alert, price)
        prev_state = alert.last_state or STATE_OK

        (
            state,
            proximity,
            threshold_desc,
            metric,
            threshold_value,
        ) = _eval_state(alert, price, move_abs, move_pct)

        alert.last_state = state
        alert.last_price = price
        alert.last_move_abs = move_abs
        alert.last_move_pct = move_pct
        alert.last_proximity_ratio = proximity
        alert.last_evaluated_at = now_iso

        alert_fired_this_cycle = False
        if state == STATE_BREACH and alert.armed and alert.enabled:
            # fire + apply recurrence
            alert.last_triggered_at = now_iso
            alert.fired_count = (getattr(alert, "fired_count", 0) or 0) + 1  # type: ignore[attr-defined]
            anchor_set_now = _handle_recurrence(alert, price, now_iso) or anchor_set_now
            alert_fired_this_cycle = True

            # track breach history
            meta["last_breach_ts"] = now_ts
            meta["last_event_type"] = "breach"
            meta["last_event_ts"] = now_ts
            meta["last_event_move_abs"] = move_abs
            meta["last_event_threshold"] = threshold_value
            recent_alert_ts.append(now_ts)
        elif prev_state == STATE_BREACH and state == STATE_OK:
            meta["last_event_type"] = "recover"
            meta["last_event_ts"] = now_ts

        alert.updated_at = now_iso
        meta["recent_alert_ts"] = recent_alert_ts

        if anchor_set_now:
            meta["last_anchor_ts"] = now_ts
            meta["last_event_type"] = "anchor"
            meta["last_event_ts"] = now_ts
            meta["last_event_threshold"] = threshold_value
            meta["last_event_move_abs"] = 0.0

        alert.metadata = meta
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
                threshold_value=threshold_value,
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
                "alert_fired_this_cycle": alert_fired_this_cycle,
                "alerts_window_count": len(recent_alert_ts),
                "alerts_window_seconds": window_seconds,
                "last_event_type": meta.get("last_event_type"),
                "last_event_ts": meta.get("last_event_ts"),
                "last_anchor_ts": meta.get("last_anchor_ts"),
                "last_breach_ts": meta.get("last_breach_ts"),
                "last_event_move_abs": meta.get("last_event_move_abs"),
                "last_event_threshold": meta.get("last_event_threshold"),
            }
        )

        # monitor status row for dl_monitors / XCom
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
            "alert_fired_this_cycle": alert_fired_this_cycle,
            "alerts_window_count": len(recent_alert_ts),
            "alerts_window_seconds": window_seconds,
            "last_event_type": meta.get("last_event_type"),
            "last_event_ts": meta.get("last_event_ts"),
            "last_anchor_ts": meta.get("last_anchor_ts"),
            "last_breach_ts": meta.get("last_breach_ts"),
            "last_event_move_abs": meta.get("last_event_move_abs"),
            "last_event_threshold": meta.get("last_event_threshold"),
        }

        statuses.append(
            {
                "monitor": "market",
                "label": alert.label or f"{alert.asset} move",
                "asset": alert.asset,
                "value": metric if metric is not None else 0.0,
                "thr_value": threshold_value,
                "thr_op": ">=",
                "state": state,
                "source": "market_core",
                "alert_fired_this_cycle": alert_fired_this_cycle,
                "alerts_window_count": len(recent_alert_ts),
                "alerts_window_seconds": window_seconds,
                "last_event_type": meta.get("last_event_type"),
                "last_event_ts": meta.get("last_event_ts"),
                "last_anchor_ts": meta.get("last_anchor_ts"),
                "last_breach_ts": meta.get("last_breach_ts"),
                "last_event_move_abs": meta.get("last_event_move_abs"),
                "last_event_threshold": meta.get("last_event_threshold"),
                "meta": meta,
            }
        )

    return {
        "ok": True,
        "source": "market_core",
        "result": {"rows": rows_for_console},
        "statuses": statuses,
    }
