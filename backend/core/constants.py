from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MOTHER_DB_PATH = BASE_DIR / "mother.db"
SONIC_SAUCE_PATH = BASE_DIR / "config" / "sonic_sauce.json"
ALERT_THRESHOLDS_PATH = BASE_DIR / "config" / "alert_thresholds.json"
CONFIG_DIR = BASE_DIR / "config"
LOG_DIR = BASE_DIR / "logs"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
JUPITER_API_BASE = "https://api.example.com"

__all__ = [
    "BASE_DIR",
    "MOTHER_DB_PATH",
    "SONIC_SAUCE_PATH",
    "ALERT_THRESHOLDS_PATH",
    "CONFIG_DIR",
    "LOG_DIR",
    "LOG_DATE_FORMAT",
    "JUPITER_API_BASE",
]
