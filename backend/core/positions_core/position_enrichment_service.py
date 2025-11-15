import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.core.calc_core.calculation_core import CalculationCore
from backend.core.logging import log
from backend.core.core_constants import MOTHER_DB_PATH
from backend.data.data_locker import DataLocker
from backend.utils.fuzzy_wuzzy import fuzzy_match_key
from backend.core.calc_core.calculation_core import CalculationCore

class PositionEnrichmentService:
    def __init__(self, data_locker=None):
        self.dl = data_locker
        self.calc_core = CalculationCore(data_locker)

    def enrich(self, position):
        from core.logging import log
        try:
            from utils.fuzzy_wuzzy import fuzzy_match_key  # type: ignore
        except ModuleNotFoundError:
            from backend.utils.fuzzy_wuzzy import fuzzy_match_key

        pos_id = position.get('id', 'UNKNOWN')
        # Ensure the asset type is present and normalized
        asset = position.get('asset_type') or position.get('asset')
        if asset:
            asset = str(asset).upper()
            position['asset_type'] = asset
        else:
            asset = 'UNKNOWN'
            position['asset_type'] = asset
            log.warning(
                f"⚠️ No asset_type for [{pos_id}] — defaulted to UNKNOWN",
                source="Enrichment",
            )

        log.info(f"\n📥 Enriching position [{pos_id}] — Asset: {asset}", source="Enrichment")

        try:
            # Step 1: Field defaults
            defaults = {
                'entry_price': 0.0,
                'current_price': position.get('entry_price', 0.0),
                'liquidation_price': 0.0,
                'collateral': 0.0,
                'size': 0.0,
                'leverage': None,
                'value': 0.0,
                'pnl_after_fees_usd': 0.0,
                'travel_percent': 0.0,
                'liquidation_distance': 0.0,
                'current_heat_index': 0.0
            }
            for k, v in defaults.items():
                position.setdefault(k, v)

            if not position.get("wallet_name"):
                position["wallet_name"] = "Unknown"
                log.warning(f"⚠️ No wallet_name for [{pos_id}] — defaulted", source="Enrichment")

            # 🔍 Step 2: Position Type Normalization
            raw_type = str(position.get("position_type", "")).strip().lower()
            if raw_type in ["long", "l"]:
                position["position_type"] = "LONG"
            elif raw_type in ["short", "s"]:
                position["position_type"] = "SHORT"
            else:
                match = fuzzy_match_key(raw_type, {"LONG": None, "SHORT": None}, threshold=60.0)
                position["position_type"] = match.upper() if match else "UNKNOWN"

            if position["position_type"] == "UNKNOWN":
                log.warning(f"⚠️ Could not normalize position_type for [{pos_id}] — input: '{raw_type}'",
                            source="Enrichment")

            # Step 3: Validation before coercion
            required_fields = ['entry_price', 'current_price', 'liquidation_price', 'collateral', 'size']
            missing = [k for k in required_fields if position.get(k) is None]
            if missing:
                log.warning(f"⚠️ Missing numeric fields for [{pos_id}]: {missing}", source="Enrichment")

            # Step 4: Safe coercion
            for field in required_fields:
                try:
                    position[field] = float(position.get(field) or 0.0)
                except Exception as e:
                    log.error(f"❌ Failed to coerce field [{field}] for [{pos_id}]: {e}", source="Enrichment")
                    position[field] = 0.0

            if position.get('value') is None:
                position['value'] = 0.0

            # Step 5: Market price injection
            latest = self.dl.get_latest_price(asset)
            if latest and 'current_price' in latest:
                position['current_price'] = float(latest['current_price'])
                log.info(f"🌐 Market price injected for {asset}: {position['current_price']}", source="Enrichment")
            # Step 6: Derived field enrichment (through CalculationCore)
            # NOTE: Jupiter already provides an accurate value field.
            # Historically we recomputed value from size * current_price,
            # but that overwrote the API-provided figure.  We keep the
            # original value now for correctness.
            # position['value'] = position['size'] * position['current_price']
            position['leverage'] = self.calc_core.calc_services.calculate_leverage(position['size'],
                                                                                   position['collateral']) if position[
                                                                                                                  'collateral'] > 0 else 0.0
            position['travel_percent'] = self.calc_core.get_travel_percent(
                position['position_type'],
                position['entry_price'], position['current_price'], position['liquidation_price']
            )
            position['liquidation_distance'] = self.calc_core.calc_services.calculate_liquid_distance(
                position['current_price'], position['liquidation_price']
            )
            if position.get('liquidation_distance') is None:
                log.warning(
                    f"⚠️ liquidation_distance is NULL for [{pos_id}] asset {asset}",
                    source="Enrichment",
                )
            try:
                risk = self.calc_core.get_heat_index(position)
            except Exception as e:
                log.error(
                    f"❌ Risk index calculation failed: {e}",
                    source="calculate_composite_risk_index",
                    payload=position,
                )
                risk = 0.0

            if risk is None:
                risk = 0.0

            position['heat_index'] = risk
            position['current_heat_index'] = risk


            log.success(f"✅ Enriched [{pos_id}] complete", source="Enrichment")
            try:
                from learning_database.learning_event_logger import log_learning_event

                payload = {
                    "position_id": pos_id,
                    "trader_name": position.get("wallet_name"),
                    "state": "ENRICH",
                    "travel_percent": position.get("travel_percent"),
                    "liquidation_distance": position.get("liquidation_distance"),
                    "heat_index": position.get("heat_index"),
                    "value": position.get("value"),
                    "leverage": position.get("leverage"),
                    "pnl_after_fees": position.get("pnl_after_fees_usd"),
                    "is_hedged": 1 if position.get("hedge_buddy_id") else 0,
                    "alert_level": position.get("alert_level", ""),
                }
                log_learning_event("position_events", payload)
            except Exception:
                pass  # logging should not interfere
            return position

        except Exception as e:
            log.error(f"🔥 Enrichment FAILED for [{pos_id}]: {e}", source="Enrichment")
            return position


def validate_enriched_position(position: dict, source="EnrichmentValidator") -> bool:
    pos_id = position.get("id", "UNKNOWN")
    failures = []

    required_fields = {
        "position_type": lambda v: v in {"LONG", "SHORT"},
        "leverage": lambda v: isinstance(v, (int, float)) and v >= 0,
        "travel_percent": lambda v: isinstance(v, (int, float)),
        "liquidation_distance": lambda v: isinstance(v, (int, float)),
        "heat_index": lambda v: isinstance(v, (int, float)),
        "value": lambda v: isinstance(v, (int, float)),
        "current_price": lambda v: isinstance(v, (int, float)),
        "wallet_name": lambda v: isinstance(v, str) and len(v) > 0,
    }

    for field, validator in required_fields.items():
        value = position.get(field)
        if value is None or not validator(value):
            failures.append((field, value))

    if failures:
        log.error(f"❌ Position [{pos_id}] failed validation on {len(failures)} fields", source=source, payload={
            f: v for f, v in failures
        })
        return False
    else:
        log.success(f"✅ Position [{pos_id}] passed all enrichment checks", source=source)
        return True
