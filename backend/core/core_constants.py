from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
# Look for MOTHER_BRAIN_DB_PATH first for backward compatibility with
# environments still using MOTHER_DB_PATH.
_brain_env = os.environ.get("MOTHER_BRAIN_DB_PATH")
_mother_env = os.environ.get("MOTHER_DB_PATH")
MOTHER_BRAIN_DB_PATH = Path(_brain_env or _mother_env or BASE_DIR / "mother.db")
MOTHER_DB_PATH = MOTHER_BRAIN_DB_PATH  # legacy alias
SONIC_SAUCE_PATH = BASE_DIR / "config" / "sonic_sauce.json"
ALERT_THRESHOLDS_PATH = BASE_DIR / "config" / "alert_thresholds.json"
CONFIG_DIR = BASE_DIR / "config"
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
    "CONFIG_DIR",
    "LOG_DIR",
    "CYCLONE_LOG_FILE",
    "SONIC_CYCLE_BUTTON",
    "LOG_DATE_FORMAT",
    "JUPITER_API_BASE",
    "MARKET_MONITOR_BLAST_RADIUS_DEFAULTS",
]
