# backend/console/config_console.py
from __future__ import annotations
from .config_console_service import run_config_console

def run_console() -> None:
    run_config_console()

if __name__ == "__main__":
    run_config_console()
