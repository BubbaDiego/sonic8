import importlib
from datetime import datetime
from backend.utils.time_utils import PACIFIC_TZ
from uuid import uuid4


def test_clear_learning_db_clears_all_tables(tmp_path, monkeypatch):
    db_path = tmp_path / "learning.db"
    monkeypatch.setenv("LEARNING_DB_PATH", str(db_path))
    import learning_database.learning_db_app as app
    importlib.reload(app)

    app.initialize_learning_db()

    cursor = app.locker.db.get_cursor()
    ts = datetime.now(PACIFIC_TZ).isoformat()

    cursor.execute(
        "INSERT INTO position_events (event_id, position_id, trader_name, ts, state, travel_percent, liquidation_distance, heat_index, value, leverage, pnl_after_fees, is_hedged, alert_level) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [str(uuid4()), "p1", "t", ts, "ENRICH", 0, 0, 0, 0, 1, 0, 0, ""],
    )
    cursor.execute(
        "INSERT INTO hedge_events (event_id, hedge_id, trader_name, ts, total_long_sz, total_short_sz, hedge_ratio, delta, total_heat_index) VALUES (?,?,?,?,?,?,?,?,?)",
        [str(uuid4()), "h1", "t", ts, 0, 0, 0, 0, 0],
    )
    cursor.execute(
        "INSERT INTO price_ticks (tick_id, asset_type, ts, price) VALUES (?,?,?,?)",
        [str(uuid4()), "BTC", ts, 1.0],
    )
    cursor.execute(
        "INSERT INTO alert_events (event_id, alert_id, trader_name, ts, alert_type, level, evaluated_value) VALUES (?,?,?,?,?,?,?)",
        [str(uuid4()), "a1", "t", ts, "type", "LOW", 0],
    )
    cursor.execute(
        "INSERT INTO trader_snapshots (snapshot_id, trader_name, ts, wallet_balance, portfolio_value, heat_index, mood, strategy_json) VALUES (?,?,?,?,?,?,?,?)",
        [str(uuid4()), "t", ts, 0, 0, 0, "", "{}"],
    )
    app.locker.db.commit()

    tables = app.locker.db.list_tables()
    for t in tables:
        assert app.locker.db.fetch_all(t)

    app.clear_learning_db()

    for t in tables:
        assert app.locker.db.fetch_all(t) == []

    app.locker.db.close()
