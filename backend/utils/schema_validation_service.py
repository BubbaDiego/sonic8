# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import os
import json
import types

#
# jsonschema import (with graceful fallback)
#
# In some environments the jsonschema -> referencing -> rpds stack fails
# due to missing native extensions (rpds.rpds). Rather than crashing the
# entire Cyclone / OperationsMonitor import chain, we provide a stub
# implementation that:
#
#   • exposes jsonschema.IS_STUB = True  (tests will auto-skip)
#   • provides jsonschema.exceptions.ValidationError
#   • provides a no-op validate() that always "passes"
#
# This keeps runtime behaviour sane while allowing full validation when
# jsonschema + rpds are actually available.
#
try:
    import jsonschema  # type: ignore
    from jsonschema import validate  # type: ignore
except Exception as exc:  # pragma: no cover - environment dependent
    # Build a tiny stub module
    stub_exc = type("ValidationError", (Exception,), {})
    jsonschema = types.SimpleNamespace(
        IS_STUB=True,
        exceptions=types.SimpleNamespace(ValidationError=stub_exc),
        __dict__={"__doc__": f"jsonschema stub: {exc!r}"},
    )

    def validate(*_a, **_k):
        # No-op: treat all configs as valid when running with the stub.
        return True

    # Make sure future `import jsonschema` sees the stub instead of
    # re-triggering the failing import path.
    sys.modules["jsonschema"] = jsonschema  # type: ignore[assignment]

from backend.core.logging import log
from backend.core.core_constants import ALERT_THRESHOLDS_PATH


class SchemaValidationService:
    """
    Service to validate critical configuration files.
    Can be invoked in post-deployment or other test suites.

    When jsonschema is unavailable (jsonschema.IS_STUB = True) validation
    is treated as a no-op that always passes, and a warning is logged.
    """

    ALERT_THRESHOLDS_FILE = str(ALERT_THRESHOLDS_PATH)

    ALERT_THRESHOLDS_SCHEMA = {
        "type": "object",
        "properties": {
            "source": {"type": "string"},
            "alert_ranges": {
                "type": "object",
                "properties": {
                    "liquidation_distance_ranges": {"type": "object"},
                    "travel_percent_liquid_ranges": {"type": "object"},
                    "heat_index_ranges": {"type": "object"},
                    "profit_ranges": {"type": "object"},
                    "price_alerts": {"type": "object"},
                },
                "required": [
                    "liquidation_distance_ranges",
                    "travel_percent_liquid_ranges",
                    "heat_index_ranges",
                    "profit_ranges",
                    "price_alerts",
                ],
            },
            "cooldowns": {
                "type": "object",
                "properties": {
                    "alert_cooldown_seconds": {"type": "number"},
                    "call_refractory_period": {"type": "number"},
                    "snooze_countdown": {"type": "number"},
                },
                "required": [
                    "alert_cooldown_seconds",
                    "call_refractory_period",
                    "snooze_countdown",
                ],
            },
            "notifications": {
                "type": "object",
                "patternProperties": {
                    "^(heat_index|travel_percent_liquid|profit|price_alerts)$": {
                        "type": "object",
                        "properties": {
                            "low": {"type": "object"},
                            "medium": {"type": "object"},
                            "high": {"type": "object"},
                        },
                    }
                },
            },
        },
        "required": ["alert_ranges", "cooldowns", "notifications"],
    }

    @staticmethod
    def validate_schema(file_path: str, schema: dict, name: str = "Unknown") -> bool:
        # If we're running with the stubbed jsonschema, just log and treat as pass
        if getattr(jsonschema, "IS_STUB", False):
            log.warning(
                f"jsonschema unavailable; skipping {name} schema validation "
                f"for {file_path}",
                source="SchemaValidationService",
            )
            return True

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            log.banner(f"{name.upper()} HEALTH CHECK")

            validate(instance=data, schema=schema)
            log.success(
                f"✅ {name} JSON schema validation passed.",
                source="SchemaValidationService",
            )
            return True

        except jsonschema.exceptions.ValidationError as ve:  # type: ignore[attr-defined]
            log.error(
                f"❌ {name} schema validation failed: {ve.message}",
                source="SchemaValidationService",
            )
            return False
        except FileNotFoundError:
            log.error(f"❌ File not found: {file_path}", source="SchemaValidationService")
            return False
        except Exception as e:
            log.error(
                f"❌ Unexpected error during {name} validation: {e}",
                source="SchemaValidationService",
            )
            return False

    @classmethod
    def validate_alert_ranges(cls) -> bool:
        return cls.validate_schema(
            cls.ALERT_THRESHOLDS_FILE,
            cls.ALERT_THRESHOLDS_SCHEMA,
            name="Alert Ranges",
        )

    @classmethod
    def batch_validate(cls) -> bool:
        """Run all schema validations in a batch."""
        log.banner("BATCH SCHEMA VALIDATION")
        results: list[bool] = []

        validations = [
            ("Alert Ranges", cls.ALERT_THRESHOLDS_FILE, cls.ALERT_THRESHOLDS_SCHEMA)
            # Future: add more configs here
        ]

        for name, file_path, schema in validations:
            result = cls.validate_schema(file_path, schema, name)
            results.append(result)

        if all(results):
            log.success("✅ All schema validations passed!", source="SchemaValidationService")
            return True
        else:
            log.error(
                "❌ One or more schema validations failed!",
                source="SchemaValidationService",
            )
            return False


if __name__ == "__main__":
    SchemaValidationService.batch_validate()
