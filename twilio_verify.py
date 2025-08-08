#!/usr/bin/env python3
"""Run Twilio authentication and optional flow using hardcoded credentials."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List

# Ensure project root is on sys.path for backend imports
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.append(str(SCRIPT_DIR.parent.parent))

from backend.scripts.twilio_test import main as twilio_test_main


def build_argv() -> List[str]:
    """Construct argument list for ``twilio_test.main`` from hardcoded values."""
    return [
        "--sid", "ACb606788ada5dccbfeeebed0f440099b3",
        "--token", "e6cbb9c3274d3aff9766e1e51e8b87bc",
        "--flow-sid", "FWc4aa959a701acd639f4ae83b338d7c42",
        "--from-phone", "+18336913467",
        "--to-phone", "+16199804758",
    ]



def main() -> int:
    argv = build_argv()
    return twilio_test_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
