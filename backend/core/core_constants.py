from pathlib import Path
import os

# resolve backend/ from this file location (…/backend/core/core_constants.py -> backend/)
_BACKEND_DIR = Path(__file__).resolve().parents[1]
_CONFIG_DIR = _BACKEND_DIR / "config"

ALERT_THRESHOLDS_PATH = Path(
    os.getenv("ALERT_THRESHOLDS_PATH", str(_CONFIG_DIR / "alert_thresholds.json"))
)

SONIC_MONITOR_CONFIG_PATH = Path(
    os.getenv("SONIC_MONITOR_CONFIG_PATH", str(_CONFIG_DIR / "sonic_monitor_config.json"))
)

XCOM_PROVIDERS_PATH = Path(
    os.getenv("SONIC_XCOM_PROVIDERS_PATH", str(_CONFIG_DIR / "xcom_providers.json"))
)

BASE_DIR = _BACKEND_DIR
# Look for MOTHER_BRAIN_DB_PATH first for backward compatibility with
# environments still using MOTHER_DB_PATH.
_brain_env = os.environ.get("MOTHER_BRAIN_DB_PATH")
_mother_env = os.environ.get("MOTHER_DB_PATH")
MOTHER_BRAIN_DB_PATH = Path(_brain_env or _mother_env or BASE_DIR / "mother.db")
MOTHER_DB_PATH = MOTHER_BRAIN_DB_PATH  # legacy alias
SONIC_SAUCE_PATH = BASE_DIR / "config" / "sonic_sauce.json"
CONFIG_DIR = _CONFIG_DIR
LOG_DIR = BASE_DIR / "logs"
CYCLONE_LOG_FILE = LOG_DIR / "cyclone_log.txt"
SONIC_CYCLE_BUTTON = BASE_DIR / "frontend" / "static" / "images" / "super_sonic.png"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
JUPITER_API_BASE = "https://perps-api.jup.ag"

# Default prices used when seeding the Market Monitor config. Update here to
# change the fallback blast radius values for BTC, ETH and SOL.
MARKET_MONITOR_BLAST_RADIUS_DEFAULTS = {"BTC": 1800.0, "ETH": 100.0, "SOL": 8.0}

__all__ = [
    "BASE_DIR",
    "MOTHER_DB_PATH",
    "MOTHER_BRAIN_DB_PATH",
    "SONIC_SAUCE_PATH",
    "ALERT_THRESHOLDS_PATH",
    "SONIC_MONITOR_CONFIG_PATH",
    "XCOM_PROVIDERS_PATH",
    "CONFIG_DIR",
    "LOG_DIR",
    "CYCLONE_LOG_FILE",
    "SONIC_CYCLE_BUTTON",
    "LOG_DATE_FORMAT",
    "JUPITER_API_BASE",
    "MARKET_MONITOR_BLAST_RADIUS_DEFAULTS",
]
