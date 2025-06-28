import importlib
from datetime import datetime, timedelta
from uuid import uuid4
import sys
import types

def test_transaction_reconstruction(tmp_path, monkeypatch):
    db_path = tmp_path / "learning.db"
    monkeypatch.setenv("LEARNING_DB_PATH", str(db_path))
    dummy = types.ModuleType("dotenv")
    dummy.load_dotenv = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "dotenv", dummy)
    import learning_database.learning_db_app as app
    importlib.reload(app)
    app.initialize_learning_db()

    cursor = app.locker.db.get_cursor()
    ts1 = datetime.now().isoformat()
    ts2 = (datetime.now() + timedelta(minutes=1)).isoformat()

    cursor.execute(
        "INSERT INTO position_events (event_id, position_id, trader_name, ts, state, travel_percent, liquidation_distance, heat_index, value, leverage, pnl_after_fees, is_hedged, alert_level) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [str(uuid4()), "p1", "trader", ts1, "ENRICH", 0, 0, 0, 100, 1, 0, 0, ""],
    )
    cursor.execute(
        "INSERT INTO position_events (event_id, position_id, trader_name, ts, state, travel_percent, liquidation_distance, heat_index, value, leverage, pnl_after_fees, is_hedged, alert_level) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [str(uuid4()), "p1", "trader", ts2, "ENRICH", 0, 0, 0, 150, 1, 0, 0, ""],
    )
    app.locker.db.commit()

    from positions.position_core import TransactionService

    svc = TransactionService(app.locker)
    txs = svc.reconstruct_transactions()
    rows = app.locker.db.fetch_all("transaction_events")

    assert len(txs) == 1
    assert len(rows) == 1
    assert rows[0]["delta_value"] == 50

    app.locker.db.close()
