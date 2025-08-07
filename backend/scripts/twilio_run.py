#!/usr/bin/env python3
"""Run Twilio authentication and optional flow using environment variables.

This helper ensures the repository's ``.env`` file is loaded even when the
script is executed from outside the project root.  Credentials are then
forwarded to :mod:`backend.scripts.twilio_test` which performs the actual
Twilio authentication and (optionally) triggers a Studio Flow.

Expected environment variables:
    TWILIO_ACCOUNT_SID   - Twilio Account SID
    TWILIO_AUTH_TOKEN    - Twilio Auth Token
    TWILIO_FLOW_SID      - (optional) Studio Flow SID
    TWILIO_PHONE_NUMBER  - (optional) From phone number
    MY_PHONE_NUMBER      - (optional) To phone number
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from typing import List

# Ensure project root is on sys.path for backend imports
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.append(str(SCRIPT_DIR.parent.parent))

from backend.scripts.twilio_test import main as twilio_test_main


def load_root_env() -> None:
    """Load a ``.env`` file located at the repository root.

    Falls back to ``.env.example`` so the script can still run with placeholder
    values during development.  Environment variables already set take
    precedence over values from the files.
    """
    root_dir = SCRIPT_DIR.parents[1]
    env_path = root_dir / ".env"
    example_path = root_dir / ".env.example"

    if not load_dotenv(env_path):
        load_dotenv(example_path)


def build_argv() -> List[str]:
    """Construct argument list for ``twilio_test.main`` from environment."""
    argv: List[str] = []
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    flow_sid = os.getenv("TWILIO_FLOW_SID")
    from_phone = os.getenv("TWILIO_PHONE_NUMBER")
    to_phone = os.getenv("MY_PHONE_NUMBER")

    if sid:
        argv += ["--sid", sid]
    if token:
        argv += ["--token", token]
    if flow_sid:
        argv += ["--flow-sid", flow_sid]
    if from_phone:
        argv += ["--from-phone", from_phone]
    if to_phone:
        argv += ["--to-phone", to_phone]
    return argv


def main() -> int:
    load_root_env()
    argv = build_argv()
    return twilio_test_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
