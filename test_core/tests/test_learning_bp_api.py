import importlib
from datetime import datetime
from uuid import uuid4

import pytest
from flask import Flask
import types
import sys


def test_transaction_events_endpoint(monkeypatch, tmp_path):
    db_path = tmp_path / "learning.db"
    monkeypatch.setenv("LEARNING_DB_PATH", str(db_path))
    # Stub flask_socketio to avoid dependency issues
    socketio_stub = types.ModuleType("flask_socketio")
    socketio_stub.Namespace = object
    monkeypatch.setitem(sys.modules, "flask_socketio", socketio_stub)
    import learning_database.learning_bp as lbp
    importlib.reload(lbp)

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(lbp.learning_bp, url_prefix="/learning")

    locker = lbp.LearningDataLocker.get_instance()
    cursor = locker.db.get_cursor()
    cursor.execute(
        "INSERT INTO transaction_events (event_id, order_id, position_id, trader_name, ts, asset_type, side, size, price, fees, pnl_estimated, classification, pre_value, post_value, delta_value, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            str(uuid4()),
            "o1",
            "p1",
            "Angie",
            datetime.utcnow().isoformat() + "Z",
            "BTC",
            "BUY",
            1.0,
            10.0,
            0.1,
            0.0,
            "OPEN",
            0.0,
            0.0,
            0.0,
            "",
        ],
    )
    locker.db.commit()

    with app.test_client() as client:
        resp = client.get("/learning/api/transaction_events/Angie?limit=1")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "transactions" in data
        assert len(data["transactions"]) == 1
        assert data["transactions"][0]["trader_name"] == "Angie"
