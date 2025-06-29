
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    redirect,
    request,
    abort,
)
from utils import iso_utc_now, normalize_iso_timestamp
import random
from trader_core.persona_avatars import AVATARS
from utils.console_logger import ConsoleLogger as log
from trader_core.mood_engine import evaluate_mood
from calc_core.calc_services import CalcServices
from oracle_core.persona_manager import PersonaManager
from wallets.wallet_core import WalletCore

PERSONA_DIR = os.path.join(os.path.dirname(__file__), "personas")
STAR_WARS_PERSONAS = [
    "C3P0",
    "Chewie",
    "Jabba",
    "Lando",
    "Leia",
    "Luke",
    "Palpatine",
    "R2",
    "Vader",
    "Yoda",
]


def _enrich_trader(trader: dict, dl, pm: PersonaManager, calc: CalcServices) -> dict:
    """Add wallet balance, heat index, performance and mood."""
    trader["born_on"] = normalize_iso_timestamp(trader.get("born_on", ""))
    name = trader.get("name")
    try:
        persona = pm.get(name)
    except KeyError:
        log.warning(f"Persona not found for trader: {name}", source="TraderBP")
        persona = None
    wallet_name = trader.get("wallet") or (
        (persona.name + "Vault") if persona else f"{name}Vault"
    )

    wallet_info = None
    if hasattr(dl, "get_wallet_by_name"):
        try:
            wallet_info = dl.get_wallet_by_name(wallet_name)
        except Exception as exc:
            log.debug(f"Wallet lookup failed: {exc}", source="TraderBP")
    if wallet_info:
        trader["public_address"] = wallet_info.get("public_address", "")

    positions = []
    if hasattr(dl, "positions"):
        pos_mgr = dl.positions
        if hasattr(pos_mgr, "get_active_positions_by_wallet"):
            positions = pos_mgr.get_active_positions_by_wallet(wallet_name) or []
        else:
            positions = pos_mgr.get_all_positions() or []

    try:
        balance = sum(float(p.get("value") or 0.0) for p in positions)
        profit = sum(calc.calculate_profit(p) for p in positions)
        trader["wallet_balance"] = round(balance, 2)
        trader["profit"] = round(profit, 2)
    except Exception as exc:
        trader["wallet_balance"] = 0.0
        trader["profit"] = 0.0
        log.debug(f"Balance/profit calculation failed: {exc}", source="TraderBP")

    avg_heat = calc.calculate_weighted_heat_index(positions)
    trader["heat_index"] = avg_heat
    trader["performance_score"] = max(0, int(100 - avg_heat))
    trader["mood"] = evaluate_mood(avg_heat, getattr(persona, "moods", {}))
    if persona:
        trader.setdefault("color", getattr(persona, "color", ""))
    return trader

trader_bp = Blueprint("trader_bp", __name__, url_prefix="/trader")

@trader_bp.route("/shop", endpoint="trader_shop")
def trader_shop():
    return render_template("trader/trader_shop.html")


@trader_bp.route("/profile/<name>")
def trader_profile_page(name: str):
    """Display a single trader profile page."""
    return render_template("trader/trader_profile.html", trader_name=name)


@trader_bp.route("/factory/<name>", methods=["GET"])
def trader_factory_page(name):
    """Legacy factory page used in tests."""
    from flask import render_template_string
    return render_template_string(f"Trader {name}")


@trader_bp.route("/cards", methods=["GET"])
def trader_cards_page():
    """Legacy cards page used in tests."""
    traders = current_app.data_locker.traders.list_traders()
    from flask import render_template_string
    names = " ".join(t.get("name", "") for t in traders)
    return render_template_string(names)


@trader_bp.route("/api/wallets", methods=["GET"])
def trader_wallets():
    """Return wallets for dropdown selections."""
    try:
        wc = getattr(getattr(current_app, "system_core", None), "wallet_core", None) or WalletCore()
        try:
            wc.refresh_wallet_balances()
        except Exception as exc:
            log.debug(f"Wallet refresh failed: {exc}", source="TraderBP")

        wallets = current_app.data_locker.read_wallets()
        simple = [
            {"name": w.get("name"), "balance": w.get("balance", 0.0)} for w in wallets
        ]
        return jsonify({"success": True, "wallets": simple})
    except Exception as e:
        log.error(f"❌ Failed to list wallets: {e}", source="API")
        return jsonify({"success": False, "error": str(e)}), 500

@trader_bp.route("/api/traders/create", methods=["POST"])
def create_trader():
    try:
        data = request.get_json()
        log.debug("Received create trader payload", source="API", payload=data)

        if not data or "name" not in data:
            log.warning("Missing 'name' in trader creation request", source="API")
            return jsonify({"success": False, "error": "Trader name required"}), 400

        # Try to parse strategy_weights if needed
        if isinstance(data.get("strategy_weights"), str):
            try:
                import json
                weights = json.loads(data["strategy_weights"])
                if isinstance(weights, dict):
                    data["strategy_weights"] = weights
                    log.debug("Parsed strategy_weights as JSON dict", source="API", payload=weights)
                else:
                    raise ValueError("strategy_weights is not a dict")
            except Exception as e:
                log.warning(f"⚠️ Could not parse strategy_weights: {e}", source="API")
                data["strategy_weights"] = {}

        # Add creation timestamp and initial collateral
        data["born_on"] = iso_utc_now()
        wallet_name = data.get("wallet")
        wallet = current_app.data_locker.get_wallet_by_name(wallet_name) if wallet_name else None
        data["initial_collateral"] = wallet.get("balance", 0.0) if wallet else 0.0

        # Call DLTraderManager directly
        manager = current_app.data_locker.traders
        try:
            success = manager.create_trader(data)
        except Exception as exc:
            reason = str(exc)
            log.error(f"Trader creation failed: {reason}", source="API")
            return jsonify({"success": False, "error": reason}), 500
        if success is False:
            reason = getattr(manager, "last_error", "Unknown error")
            log.error(f"Trader creation failed: {reason}", source="API")
            return jsonify({"success": False, "error": reason}), 500

        log.success(f"✅ Trader created: {data['name']}", source="API")
        return jsonify({"success": True})

    except Exception as e:
        import traceback
        log.error(f"❌ Exception in trader creation: {e}", source="API")
        log.debug(traceback.format_exc(), source="API")
        return jsonify({"success": False, "error": str(e)}), 500


@trader_bp.route("/api/traders/create_star_wars", methods=["POST"])
def create_star_wars_traders():
    """Create traders for predefined Star Wars personas."""
    try:
        pm = PersonaManager()
        names = [
            "C3P0",
            "Chewie",
            "Jabba",
            "Lando",
            "Leia",
            "Luke",
            "Palpatine",
            "R2",
            "Vader",
            "Yoda",
        ]
        mood_words = list({
            "nervous",
            "roaring",
            "ruthless",
            "charming",
            "resolute",
            "determined",
            "power_hungry",
            "beeping",
            "calm",
        })
        created = []
        for name in names:
            persona = pm.get(name)
            wallet_name = f"{name}Vault"
            wallet = current_app.data_locker.get_wallet_by_name(wallet_name)
            balance = wallet.get("balance", 0.0) if wallet else 0.0
            avatar_key = getattr(persona, "avatar", name)
            avatar = AVATARS.get(avatar_key, {}).get("icon", avatar_key)
            mood1, mood2 = random.sample(mood_words, 2)
            data = {
                "name": persona.name,
                "avatar": avatar,
                "color": getattr(persona, "color", ""),
                "wallet": wallet_name,
                "born_on": iso_utc_now(),
                "initial_collateral": balance,
                "mood": mood1,
                "moods": {"high_heat": mood1, "stable": mood2},
            }
            current_app.data_locker.traders.create_trader(data)
            created.append(name)

        return jsonify({"success": True, "created": created})
    except Exception as e:
        log.error(f"❌ Failed to create Star Wars traders: {e}", source="API")
        return jsonify({"success": False, "error": str(e)}), 500


@trader_bp.route("/api/traders/quick_import", methods=["POST"])
def quick_import_traders():
    """Create traders from active wallets when the name loosely matches a persona."""
    try:
        wallets = current_app.data_locker.read_wallets()
        active = [w for w in wallets if w.get("is_active", True)]
        pm = PersonaManager()
        persona_names = list(pm.list_personas())
        created = []
        for w in active:
            wname = w.get("name", "")
            match = next((p for p in persona_names if p.lower() in wname.lower()), None)
            if not match:
                continue
            persona = pm.get(match)
            avatar_key = getattr(persona, "avatar", match)
            avatar = AVATARS.get(avatar_key, {}).get("icon", avatar_key)
            data = {
                "name": persona.name,
                "avatar": avatar,
                "color": getattr(persona, "color", ""),
                "wallet": wname,
                "born_on": iso_utc_now(),
                "initial_collateral": w.get("balance", 0.0),
            }
            current_app.data_locker.traders.create_trader(data)
            created.append(persona.name)

        return jsonify({"success": True, "created": created})
    except Exception as e:
        log.error(f"❌ Failed to quick import traders: {e}", source="API")
        return jsonify({"success": False, "error": str(e)}), 500


@trader_bp.route("/api/persona_colors", methods=["GET"])
def get_persona_colors():
    """Return color mappings for Star Wars personas."""
    pm = PersonaManager(base_dir=PERSONA_DIR)
    colors = {}
    for name in STAR_WARS_PERSONAS:
        try:
            persona = pm.get(name)
            colors[name] = getattr(persona, "color", "")
        except KeyError:
            continue
    return jsonify(colors)


@trader_bp.route("/api/persona_colors/<name>", methods=["POST"])
def save_persona_color(name):
    """Update a persona's color in its JSON file."""
    is_json = getattr(request, "is_json", True)
    body = request.json if hasattr(request, "json") else (request.get_json() if hasattr(request, "get_json") else None)
    color = body.get("color") if is_json and isinstance(body, dict) else None
    if not color:
        return jsonify({"success": False, "error": "Missing color"}), 400
    path = os.path.join(PERSONA_DIR, f"{name}.json")
    if not os.path.exists(path):
        return jsonify({"success": False, "error": "Persona not found"}), 404
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        data["color"] = color
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return jsonify({"success": True})
    except Exception as e:
        log.error(f"❌ Failed to save persona color: {e}", source="API")
        return jsonify({"success": False, "error": str(e)}), 500

@trader_bp.route("/api/traders/<name>", methods=["GET"])
def get_trader(name):
    try:
        log.info(f"Fetching trader: {name}", source="API")
        trader = current_app.data_locker.traders.get_trader_by_name(name)
        if not trader:
            log.warning(f"Trader not found: {name}", source="API")
            return jsonify({"success": False, "error": "Trader not found"}), 404

        pm = PersonaManager()
        calc = CalcServices()
        trader = _enrich_trader(trader, current_app.data_locker, pm, calc)

        return jsonify({"success": True, "trader": trader})
    except Exception as e:
        log.error(f"❌ Failed to fetch trader: {e}", source="API")
        return jsonify({"success": False, "error": str(e)}), 500

@trader_bp.route("/api/traders", methods=["GET"])
def list_traders():
    try:
        log.info("Listing all traders", source="API")
        wc = getattr(getattr(current_app, "system_core", None), "wallet_core", None) or WalletCore()
        try:
            wc.refresh_wallet_balances()
        except Exception as exc:
            log.debug(f"Wallet refresh failed: {exc}", source="TraderBP")

        traders = current_app.data_locker.traders.list_traders()
        pm = PersonaManager()
        calc = CalcServices()
        enriched = [_enrich_trader(t, current_app.data_locker, pm, calc) for t in traders]
        return jsonify({"success": True, "traders": enriched})
    except Exception as e:
        log.error(f"❌ Failed to list traders: {e}", source="API")
        return jsonify({"success": False, "error": str(e)}), 500

@trader_bp.route("/api/traders/<name>", methods=["PUT"])
def update_trader(name):
    try:
        fields = request.get_json()
        log.debug(f"Updating trader {name}", source="API", payload=fields)
        current_app.data_locker.traders.update_trader(name, fields)
        return jsonify({"success": True})
    except Exception as e:
        log.error(f"❌ Failed to update trader: {e}", source="API")
        return jsonify({"success": False, "error": str(e)}), 500

@trader_bp.route("/api/traders/<name>/delete", methods=["DELETE"])
def delete_trader(name):
    try:
        log.info(f"Deleting trader: {name}", source="API")
        deleted = current_app.data_locker.traders.delete_trader(name)
        if not deleted:
            log.warning(f"Trader not found for deletion: {name}", source="API")
            return jsonify({"success": False, "error": "Trader not found"}), 404
        return jsonify({"success": True})
    except Exception as e:
        log.error(f"❌ Failed to delete trader: {e}", source="API")
        return jsonify({"success": False, "error": str(e)}), 500


@trader_bp.route("/api/traders/delete_all", methods=["POST"])
def delete_all_traders():
    """Delete every trader entry."""
    try:
        current_app.data_locker.traders.delete_all_traders()
        return jsonify({"success": True})
    except Exception as e:
        log.error(f"❌ Failed to delete all traders: {e}", source="API")
        return jsonify({"success": False, "error": str(e)}), 500


@trader_bp.route("/api/traders/export", methods=["POST"])
def export_traders():
    """Export all traders to ``active_traders.json`` and send the file."""
    from flask import send_file
    from data import dl_traders as dl_t

    try:
        path = str(dl_t.ACTIVE_TRADERS_JSON_PATH)
        current_app.data_locker.traders.export_to_json(path)
        return send_file(path, as_attachment=True, download_name=os.path.basename(path))
    except Exception as e:
        log.error(f"❌ Failed to export traders: {e}", source="API")
        return jsonify({"success": False, "error": str(e)}), 500


@trader_bp.route("/api/traders/import", methods=["POST"])
def import_traders():
    """Import traders from an uploaded JSON file or ``active_traders.json``."""
    files = getattr(request, "files", None)
    file = files.get("file") if files else None
    data = None
    if file:
        try:
            data = json.load(file)
        except Exception as e:
            log.error(f"❌ Failed to parse uploaded traders JSON: {e}", source="API")
            return jsonify({"success": False, "error": str(e)}), 400
    elif getattr(request, "json", None) is not None:
        data = request.json
    elif getattr(request, "data", None):
        try:
            data = json.loads(request.data.decode("utf-8"))
        except Exception:
            data = None

    if isinstance(data, list):
        count = 0
        for item in data:
            if isinstance(item, dict) and item.get("name"):
                current_app.data_locker.traders.create_trader(item)
                count += 1
        return jsonify({"success": True, "imported": count})

    try:
        count = current_app.data_locker.traders.import_from_json()
        return jsonify({"success": True, "imported": count})
    except Exception as e:
        log.error(f"❌ Failed to import traders: {e}", source="API")
        return jsonify({"success": False, "error": str(e)}), 500

