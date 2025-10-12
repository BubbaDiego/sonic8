from __future__ import annotations
import os

# Visible spinner for at least this many seconds (see requirements)
MIN_SPINNER_SECONDS: float = float(os.getenv("SONIC_MIN_SPINNER_SECONDS", "1.5"))
SPINNER_INTERVAL: float = float(os.getenv("SONIC_SPINNER_INTERVAL", "0.12"))
PRICE_TTL_SECONDS: float = float(os.getenv("SONIC_PRICE_TTL_SECONDS", "30"))

# Toggle wallet-by-wallet noisy lines (off by default)
TASKS_VERBOSE: int = int(os.getenv("SONIC_TASKS_VERBOSE", "0"))

# A small set of pleasant spinners; one is picked at random per task
SPINNERS = [
    list("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"),
    list("|/-\\"),
    list("←↖↑↗→↘↓↙"),
    list("▖▘▝▗"),
    list("·∙●∙"),
]
