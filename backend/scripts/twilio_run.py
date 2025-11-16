#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv  # type: ignore

# ---------------------------------------------------------------------------
# Env bootstrap: load .env from repo root so we get TWILIO_* vars.
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parents[2]

# Try .env, fall back to .env.example
if not load_dotenv(ROOT_DIR / ".env"):
    load_dotenv(ROOT_DIR / ".env.example")

# Make sure we can import backend.*
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.scripts.twilio_test import main as twilio_test_main  # type: ignore


def _build_argv(mode: str) -> List[str]:
    """
    Build argv to pass into twilio_test.main() based on env + chosen mode.

    mode == "auth" → only verify SID/token
    mode == "call" → verify SID/token AND attempt a Studio Flow voice call
                     if TWILIO_FLOW_SID + phones are present.
    """
    sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    token = os.getenv("TWILIO_AUTH_TOKEN", "")

    if not sid or not token:
        print("[Twilio] Missing TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN in environment.")
        return []

    args: List[str] = ["--sid", sid, "--token", token]

    if mode == "call":
        flow_sid = os.getenv("TWILIO_FLOW_SID", "")
        from_phone = (
            os.getenv("TWILIO_FROM_PHONE")
            or os.getenv("TWILIO_PHONE_NUMBER", "")
        )
        to_phone = (
            os.getenv("TWILIO_TO_PHONE")
            or os.getenv("MY_PHONE_NUMBER", "")
        )

        if flow_sid and from_phone and to_phone:
            args += [
                "--flow-sid",
                flow_sid,
                "--from-phone",
                from_phone,
                "--to-phone",
                to_phone,
            ]
        else:
            print(
                "[Twilio] Call mode requested but TWILIO_FLOW_SID / "
                "TWILIO_FROM_PHONE / TWILIO_TO_PHONE (or MY_PHONE_NUMBER) "
                "are not all set. Falling back to auth-only."
            )

    return args


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Env-driven Twilio verifier (auth-only or auth+call)."
    )
    parser.add_argument(
        "--mode",
        choices=["auth", "call"],
        default="auth",
        help="auth = only verify creds; call = verify + test voice call via Studio Flow",
    )
    ns = parser.parse_args(argv)

    args = _build_argv(ns.mode)
    if not args:
        return 1

    # Delegate to the real CLI implementation
    return twilio_test_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
