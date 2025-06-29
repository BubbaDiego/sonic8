# ──────────────────────────────────────────────────────────────
#  File: api/hedge_wizard_bp.py
#  Author: BubbaDiego
#  Created: 2025‑06‑24
#  Description:
#      Flask blueprint exposing Auto‑Hedge Wizard endpoints:
#          GET  /suggest
#          POST /execute
# ──────────────────────────────────────────────────────────────
from flask import Blueprint, request, jsonify, current_app
from hedge_core.auto_hedge_wizard import AutoHedgeWizardCore

wizard_bp = Blueprint("wizard_bp", __name__, url_prefix="/sonic_labs/api/wizard")

def _core() -> AutoHedgeWizardCore:
    return AutoHedgeWizardCore(current_app.config["DATA_LOCKER"])

@wizard_bp.route("/suggest")
def suggest():
    hedge_id = request.args.get("hedge_id")
    price     = float(request.args.get("price", 0))
    mode      = request.args.get("mode", "equal_value")
    target    = float(request.args.get("target", 12))
    side      = request.args.get("side", "long")

    dl = current_app.config["DATA_LOCKER"]
    long, short = dl.hedges.get_long_short_positions(hedge_id)  # helper you already have
    core = _core()

    if mode == "liq_dist":
        suggestion = core.suggest_liq_distance(long, short, price, target, side)
    else:
        suggestion = core.suggest_equal_value(long, short, price)

    return jsonify({"order_definition": suggestion, "metrics": {"mode": mode}})

@wizard_bp.route("/execute", methods=["POST"])
def execute():
    order_def = request.json or {}
    core = _core()
    result = core.execute_order(order_def)
    return jsonify({"status": "queued", "order": result})
