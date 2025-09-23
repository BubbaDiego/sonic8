"""End-to-end market pipeline probe (no external deps beyond requests).

1. Dump inputs (thresholds/anchors/prices) via debug endpoint or locker.
2. Compute 'would_trigger' per asset (pure preview).
3. Run the market monitor once via /monitors/market_monitor.
4. Fetch /api/market/latest and print what the UI consumes.

Environment variables
---------------------
SONIC_API_URL (default autodetect; prefers http://localhost:3000)
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict

import requests

DEFAULTS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
]
API_ENV = os.getenv("SONIC_API_URL")
CLI_BASE = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].startswith("http") else None
TIMEOUT_SHORT = float(os.getenv("SONIC_HTTP_TIMEOUT_SHORT", "5"))
TIMEOUT_LONG = float(os.getenv("SONIC_HTTP_TIMEOUT_LONG", "20"))


def jprint(obj: Any, title: str) -> None:
    print(f"\n{title}")
    print("=" * len(title))
    print(json.dumps(obj, indent=2, sort_keys=True))


def get(url: str) -> Dict[str, Any]:
    response = requests.get(url, timeout=TIMEOUT_SHORT)
    response.raise_for_status()
    return response.json()


def post(url: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    response = requests.post(url, json=payload or {}, timeout=TIMEOUT_LONG)
    response.raise_for_status()
    return response.json()


def detect_api_base() -> str:
    """Return the API base URL following precedence rules."""

    if CLI_BASE:
        return CLI_BASE.rstrip("/")

    if API_ENV:
        return API_ENV.rstrip("/")

    for base in DEFAULTS:
        try:
            response = requests.get(f"{base}/api/market/latest", timeout=2)
            if response.status_code < 500:
                return base
        except Exception:  # pragma: no cover - best effort detection
            continue

    return DEFAULTS[0]


def main() -> None:
    base = detect_api_base()
    print(f"API_BASE={base}")

    # 1) Inputs (config + anchors + prices)
    try:
        state = get(f"{base}/debug/market/state")
        jprint(state, "MARKET INPUT STATE")
    except Exception as exc:  # pragma: no cover - diagnostic script
        print(f"warn: /debug/market/state failed: {exc}")
        state = {}

    try:
        eval_preview = get(f"{base}/debug/market/eval")
        jprint(eval_preview, "PURE EVAL (WOULD-TRIGGER PREVIEW)")
    except Exception as exc:  # pragma: no cover - diagnostic script
        print(f"warn: /debug/market/eval failed: {exc}")

    # 2) Kick monitor once
    try:
        run = post(f"{base}/monitors/market_monitor")
        jprint(run, "RUN MARKET MONITOR ONCE")
    except Exception as exc:  # pragma: no cover - diagnostic script
        print(f"error: POST /monitors/market_monitor failed: {exc}")

    # brief pause for ledger write
    time.sleep(0.5)

    # 3) What the UI reads
    try:
        latest = get(f"{base}/api/market/latest")
        jprint(latest, "API /api/market/latest (UI payload)")
    except Exception as exc:  # pragma: no cover - diagnostic script
        print(f"error: GET /api/market/latest failed: {exc}")


if __name__ == "__main__":
    main()
