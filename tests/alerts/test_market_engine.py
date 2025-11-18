import pytest

from backend.models.price_alert import PriceAlert
from backend.core.market_core import market_engine


# Re-exported constants so tests read clearly.
STATE_OK = market_engine.STATE_OK
STATE_WARN = market_engine.STATE_WARN
STATE_BREACH = market_engine.STATE_BREACH
STATE_DISARMED = market_engine.STATE_DISARMED

_compute_moves = market_engine._compute_moves
_eval_state = market_engine._eval_state
_handle_recurrence = market_engine._handle_recurrence
evaluate_market_alerts = market_engine.evaluate_market_alerts


# ---------------------------------------------------------------------------
# Test helpers / stubs
# ---------------------------------------------------------------------------


class StubAlertsManager:
    """Minimal stub for dl.price_alerts."""

    def __init__(self, alerts):
        self._alerts = list(alerts)
        self.saved_alerts = []

    def list_alerts(self):
        # evaluate_market_alerts iterates over these
        return list(self._alerts)

    def save_alert(self, alert: PriceAlert):
        # Track what was saved so tests can assert on side effects.
        self.saved_alerts.append(alert)


class StubEventsManager:
    """Minimal stub for dl.price_alert_events."""

    def __init__(self):
        self.events = []

    def record_event(self, event):
        self.events.append(event)


class StubDL:
    """DataLocker stub for evaluate_market_alerts."""

    def __init__(self, alerts):
        self.price_alerts = StubAlertsManager(alerts)
        self.price_alert_events = StubEventsManager()


def make_move_alert(
    *,
    asset: str = "BTC",
    rule_type: str = "move_pct",
    direction: str = "both",
    threshold: float = 5.0,
    anchor: float | None = 100.0,
    enabled: bool = True,
    recurrence_mode: str = "single",
) -> PriceAlert:
    """Helper to build a PriceAlert focused on move rules."""
    return PriceAlert(
        asset=asset,
        rule_type=rule_type,
        direction=direction,
        base_threshold_value=threshold,
        current_anchor_price=anchor,
        current_anchor_time="2020-01-01T00:00:00",
        enabled=enabled,
        recurrence_mode=recurrence_mode,
    )


def make_target_alert(
    *,
    asset: str = "BTC",
    direction: str = "above",
    target_price: float = 100.0,
    enabled: bool = True,
) -> PriceAlert:
    """Helper to build a PriceAlert for price_target rules."""
    return PriceAlert(
        asset=asset,
        rule_type="price_target",
        direction=direction,
        base_threshold_value=target_price,
        current_anchor_price=target_price,
        current_anchor_time="2020-01-01T00:00:00",
        enabled=enabled,
    )


def make_simple_move_abs_alert(
    *,
    asset: str = "BTC",
    threshold: float = 10.0,
    anchor: float = 100.0,
    recurrence_mode: str = "single",
) -> PriceAlert:
    """Helper tuned for recurrence tests (move_abs rules)."""
    return PriceAlert(
        asset=asset,
        rule_type="move_abs",
        direction="both",
        base_threshold_value=threshold,
        current_anchor_price=anchor,
        current_anchor_time="2020-01-01T00:00:00",
        enabled=True,
        recurrence_mode=recurrence_mode,
        armed=True,
    )


# ---------------------------------------------------------------------------
# Basic movement / anchor math
# ---------------------------------------------------------------------------


def test_compute_moves_returns_zero_when_no_anchor():
    alert = PriceAlert(asset="BTC", base_threshold_value=5.0)
    move_abs, move_pct = _compute_moves(alert, price=110.0)
    assert move_abs == 0.0
    assert move_pct == 0.0


def test_compute_moves_from_anchor():
    alert = PriceAlert(
        asset="BTC",
        base_threshold_value=5.0,
        current_anchor_price=100.0,
    )
    move_abs, move_pct = _compute_moves(alert, price=110.0)
    assert move_abs == pytest.approx(10.0)
    assert move_pct == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# Direction handling for move_pct / move_abs
# ---------------------------------------------------------------------------


def test_move_pct_up_only_triggers_on_upward_moves():
    alert = make_move_alert(direction="up", threshold=5.0, anchor=100.0)

    # Price below anchor: should NOT trigger, metric should collapse to zero.
    move_abs, move_pct = _compute_moves(alert, price=90.0)
    state, proximity, _, metric, thr = _eval_state(alert, 90.0, move_abs, move_pct)
    assert state == STATE_OK
    assert metric == pytest.approx(0.0)
    assert proximity == pytest.approx(0.0)
    assert thr == pytest.approx(5.0)

    # Price above anchor: should breach.
    move_abs, move_pct = _compute_moves(alert, price=110.0)
    state, proximity, desc, metric, thr = _eval_state(alert, 110.0, move_abs, move_pct)
    assert state == STATE_BREACH
    assert metric == pytest.approx(10.0)  # percent move
    assert thr == pytest.approx(5.0)
    assert "move" in desc
    assert 0.0 <= proximity <= 1.0


def test_move_pct_down_only_triggers_on_downward_moves():
    alert = make_move_alert(direction="down", threshold=5.0, anchor=100.0)

    # Up move should be ignored for "down".
    move_abs, move_pct = _compute_moves(alert, price=110.0)
    state, proximity, _, metric, _ = _eval_state(alert, 110.0, move_abs, move_pct)
    assert state == STATE_OK
    assert metric == pytest.approx(0.0)
    assert proximity == pytest.approx(0.0)

    # Down move should breach.
    move_abs, move_pct = _compute_moves(alert, price=90.0)
    state, _, _, metric, thr = _eval_state(alert, 90.0, move_abs, move_pct)
    assert state == STATE_BREACH
    assert metric == pytest.approx(10.0)
    assert thr == pytest.approx(5.0)


def test_move_pct_both_uses_absolute_movement():
    alert = make_move_alert(direction="both", threshold=5.0, anchor=100.0)

    move_abs, move_pct = _compute_moves(alert, price=90.0)
    state, _, _, metric, _ = _eval_state(alert, 90.0, move_abs, move_pct)
    # 10% down with threshold 5% should breach.
    assert state == STATE_BREACH
    assert metric == pytest.approx(10.0)


def test_move_pct_warn_zone_at_seventy_percent_of_threshold():
    alert = make_move_alert(direction="both", threshold=10.0, anchor=100.0)

    # 7% move vs 10% threshold → ratio 0.7 → WARN
    move_abs, move_pct = _compute_moves(alert, price=107.0)
    state, proximity, desc, metric, thr = _eval_state(alert, 107.0, move_abs, move_pct)

    assert state == STATE_WARN
    assert pytest.approx(proximity, rel=1e-5) == 0.7
    assert metric == pytest.approx(7.0)
    assert thr == pytest.approx(10.0)
    assert "move" in desc


def test_move_abs_uses_absolute_dollars():
    alert = make_move_alert(
        rule_type="move_abs", direction="both", threshold=10.0, anchor=100.0
    )

    move_abs, move_pct = _compute_moves(alert, price=90.0)
    state, _, desc, metric, thr = _eval_state(alert, 90.0, move_abs, move_pct)

    # $10 move from anchor with $10 threshold → breach.
    assert state == STATE_BREACH
    assert metric == pytest.approx(10.0)
    assert thr == pytest.approx(10.0)
    assert desc.startswith("$10.00")


def test_eval_state_respects_enabled_flag():
    alert = make_move_alert(enabled=False, anchor=100.0)

    move_abs, move_pct = _compute_moves(alert, price=120.0)
    state, proximity, _, metric, _ = _eval_state(alert, 120.0, move_abs, move_pct)

    assert state == STATE_DISARMED
    # For a disabled alert, proximity / metric aren't used for firing.
    assert proximity >= 0.0
    assert metric is not None


# ---------------------------------------------------------------------------
# price_target behavior (above / below)
# ---------------------------------------------------------------------------


def test_price_target_above_warn_and_breach():
    alert = make_target_alert(direction="above", target_price=100.0)

    # Close but not breached → WARN
    state, proximity, desc, metric, thr = _eval_state(alert, 95.0, 0.0, 0.0)
    assert state == STATE_WARN
    assert "≥ 100.00" in desc
    assert metric == pytest.approx(95.0)
    assert thr == pytest.approx(100.0)
    assert 0.0 < proximity < 1.0

    # Crosses above → BREACH
    state2, proximity2, desc2, metric2, thr2 = _eval_state(alert, 110.0, 0.0, 0.0)
    assert state2 == STATE_BREACH
    assert "≥ 100.00" in desc2
    assert metric2 == pytest.approx(110.0)
    assert thr2 == pytest.approx(100.0)
    assert proximity2 == pytest.approx(1.0)


def test_price_target_below_warn_and_breach():
    alert = make_target_alert(direction="below", target_price=100.0)

    # Slightly above target → WARN (moving towards trigger).
    state, proximity, desc, metric, thr = _eval_state(alert, 105.0, 0.0, 0.0)
    assert state == STATE_WARN
    assert "≤ 100.00" in desc
    assert metric == pytest.approx(105.0)
    assert thr == pytest.approx(100.0)
    assert 0.0 < proximity < 1.0

    # Below target → BREACH
    state2, proximity2, desc2, metric2, thr2 = _eval_state(alert, 90.0, 0.0, 0.0)
    assert state2 == STATE_BREACH
    assert "≤ 100.00" in desc2
    assert metric2 == pytest.approx(90.0)
    assert thr2 == pytest.approx(100.0)
    assert proximity2 == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Recurrence modes: single / reset / ladder
# ---------------------------------------------------------------------------


def test_single_recurrence_disarms_after_breach_and_logs_event():
    alert = make_simple_move_abs_alert(recurrence_mode="single")
    dl = StubDL([alert])

    result = evaluate_market_alerts(dl, {"BTC": 115.0})

    # State & recurrence
    assert alert.last_state == STATE_BREACH
    assert alert.armed is False
    assert alert.fired_count == 1

    # Event logging
    assert len(dl.price_alert_events.events) == 1
    event = dl.price_alert_events.events[0]
    assert event.event_type == "breach"
    assert event.asset == "BTC"
    assert result["statuses"][0]["state"] == STATE_BREACH
    assert result["statuses"][0]["meta"]["recurrence_mode"] == "single"


def test_reset_recurrence_moves_anchor_and_allows_future_breaches():
    alert = make_simple_move_abs_alert(recurrence_mode="reset")
    dl = StubDL([alert])

    # First breach from 100 → 115
    evaluate_market_alerts(dl, {"BTC": 115.0})
    first_anchor = alert.current_anchor_price
    assert first_anchor == pytest.approx(115.0)
    assert alert.armed is True
    assert alert.fired_count == 1

    # Second evaluation at same price should now be OK (move_abs = 0)
    evaluate_market_alerts(dl, {"BTC": 115.0})
    assert alert.last_state == STATE_OK

    # Move further away to trigger again
    evaluate_market_alerts(dl, {"BTC": 130.0})
    assert alert.last_state == STATE_BREACH
    assert alert.current_anchor_price == pytest.approx(130.0)
    assert alert.fired_count == 2


def test_ladder_recurrence_steps_anchor_but_preserves_original():
    alert = make_simple_move_abs_alert(recurrence_mode="ladder")
    dl = StubDL([alert])

    # Initial breach, anchor moves from 100 → 115
    evaluate_market_alerts(dl, {"BTC": 115.0})
    assert alert.original_anchor_price == pytest.approx(100.0)
    assert alert.current_anchor_price == pytest.approx(115.0)
    assert alert.fired_count == 1

    # Next step up should breach again and move anchor to 130
    evaluate_market_alerts(dl, {"BTC": 130.0})
    assert alert.current_anchor_price == pytest.approx(130.0)
    # Ladder keeps original anchor for history / UI
    assert alert.original_anchor_price == pytest.approx(100.0)
    assert alert.fired_count == 2


# ---------------------------------------------------------------------------
# evaluate_market_alerts: basic plumbing / statuses
# ---------------------------------------------------------------------------


def test_evaluate_market_alerts_summarizes_status_rows():
    alert = make_move_alert(
        rule_type="move_pct",
        direction="up",
        threshold=5.0,
        anchor=100.0,
    )
    dl = StubDL([alert])

    result = evaluate_market_alerts(dl, {"BTC": 110.0})

    assert result["ok"] is True
    assert result["source"] == "market_core"

    rows = result["result"]["rows"]
    assert len(rows) == 1
    row = rows[0]
    assert row["asset"] == "BTC"
    assert row["state"] == STATE_BREACH
    assert row["anchor_price"] == pytest.approx(100.0)

    statuses = result["statuses"]
    assert len(statuses) == 1
    status = statuses[0]
    assert status["monitor"] == "market"
    assert status["asset"] == "BTC"
    assert status["state"] == STATE_BREACH
    assert status["thr_value"] == pytest.approx(5.0)
    assert status["thr_op"] == ">="
    meta = status["meta"]
    assert meta["rule_type"] == "move_pct"
    assert meta["direction"] == "up"
    assert meta["recurrence_mode"] == "single"

