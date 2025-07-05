from flask import Blueprint, jsonify, render_template, request
from flask_socketio import Namespace
from datetime import datetime, timedelta
import threading
import time
from learning_database.learning_data_locker import LearningDataLocker


learning_bp = Blueprint(
    "learning_db",
    __name__,
    template_folder="../templates/learning_db",
    static_folder="../static",
)


# learning_bp.py
@learning_bp.route("/api/metrics/profit")
def api_profit():
    trader = request.args.get("trader")
    cursor = LearningDataLocker.get_instance().db.get_cursor()
    cursor.execute("""
        SELECT ts, pnl_estimated
        FROM transaction_events
        WHERE trader_name = ?
        ORDER BY ts
    """, (trader,))
    rows = cursor.fetchall()

    profit = 0
    data = []
    for row in rows:
        profit += row["pnl_estimated"] or 0
        data.append({"ts": row["ts"], "value": profit})

    return jsonify(data)




@learning_bp.route("/api/metrics/heat_series")
def api_heat():
    trader = request.args.get("trader")
    cursor = LearningDataLocker.get_instance().db.get_cursor()
    cursor.execute("""
        SELECT ts,
               AVG(COALESCE(heat_index, 0))
                 OVER (ORDER BY ts) AS value
        FROM position_events
        WHERE trader_name = ?
        ORDER BY ts
    """, (trader,))
    rows = [dict(r) for r in cursor.fetchall()]
    return jsonify(rows)



@learning_bp.route("/")
def learning_index():
    return render_template("learning_db/learning_index.html")


class LearningNamespace(Namespace):
    def __init__(self, namespace=None, **kwargs):
        super().__init__(namespace, **kwargs)

    def on_connect(self):
        print("[learning/ws] client connected")

    def on_disconnect(self):
        print("[learning/ws] client disconnected")


def start_metric_streamer(socketio, app):
    socketio.on_namespace(LearningNamespace("/learning"))

    def emit_metrics():
        locker = LearningDataLocker.get_instance()

        while True:
            cursor = locker.db.get_cursor()

            cursor.execute("SELECT value FROM position_events ORDER BY ts DESC LIMIT 1")
            latest_profit = cursor.fetchone()

            cursor.execute(
                "SELECT heat_index FROM position_events ORDER BY ts DESC LIMIT 1"
            )
            latest_heat = cursor.fetchone()

            payload = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "profit": latest_profit[0] if latest_profit else 0,
                "heat": latest_heat[0] if latest_heat else 0,
            }
            socketio.emit("metric_update", payload, namespace="/learning")
            # print(f"Emitting metrics: {payload}")  # Debug log
            time.sleep(60)

    threading.Thread(target=emit_metrics, daemon=True).start()


@learning_bp.route('/api/position_events')
def api_position_events():
    trader = request.args.get('trader')
    limit  = int(request.args.get('limit', 100))
    cursor = LearningDataLocker.get_instance().db.get_cursor()
    cursor.execute("""
        SELECT * FROM position_events
        WHERE trader_name = ?
          AND state = 'ENRICH'
        ORDER BY ts DESC
        LIMIT ?
    """, (trader, limit))
    return jsonify({"events": [dict(r) for r in cursor.fetchall()]})


@learning_bp.route("/api/transaction_events")
def api_transaction_events():
    limit = int(request.args.get("limit", 100))
    cursor = LearningDataLocker.get_instance().db.get_cursor()
    cursor.execute(
        "SELECT * FROM transaction_events ORDER BY ts DESC LIMIT ?",
        (limit,),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    return jsonify({"transactions": rows})


@learning_bp.route("/api/transaction_events/<trader_name>")
def api_transaction_events_for_trader(trader_name: str):
    """Return recent transactions for the specified trader."""
    limit = int(request.args.get("limit", 200))
    cur = LearningDataLocker.get_instance().db.get_cursor()
    cur.execute(
        """
        SELECT * FROM transaction_events
        WHERE trader_name = ?
        ORDER BY ts DESC
        LIMIT ?
        """,
        (trader_name, limit),
    )
    rows = [dict(r) for r in cur.fetchall()]
    return jsonify({"transactions": rows})


@learning_bp.route("/api/trader_performance")
def trader_performance():
    """Return net PnL totals per trader for Chart.js visualizations."""
    cursor = LearningDataLocker.get_instance().db.get_cursor()
    cursor.execute(
        """
        SELECT trader_name, SUM(pnl_estimated) AS total_pnl
        FROM transaction_events
        GROUP BY trader_name
        ORDER BY total_pnl DESC
        """
    )
    rows = cursor.fetchall()
    labels = [row["trader_name"] for row in rows]
    pnl_values = [
        round(row["total_pnl"], 2) if row["total_pnl"] is not None else 0
        for row in rows
    ]
    return jsonify(
        {
            "labels": labels,
            "datasets": [{"label": "Trader Net PnL (USD)", "data": pnl_values}],
        }
    )


@learning_bp.route("/api/reconstruct_transactions", methods=["POST"])
def reconstruct_transactions_api():
    """Rebuild transaction_events table from position_events."""
    try:
        from backend.core.positions_core.position_core import TransactionService

        locker = LearningDataLocker.get_instance()
        service = TransactionService(locker)
        txs = service.reconstruct_transactions()
        return jsonify({"message": f"{len(txs)} transactions reconstructed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
