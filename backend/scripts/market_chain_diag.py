"""End-to-end market pipeline probe (no external deps beyond requests).

1. Dump inputs (thresholds/anchors/prices) via debug endpoint or locker.
2. Compute 'would_trigger' per asset (pure preview).
3. Run the market monitor once via /monitors/market_monitor.
4. Fetch /api/market/latest and print what the UI consumes.

Environment variables
---------------------
SONIC_API_URL (default http://localhost:5000)
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

import requests

API = os.getenv("SONIC_API_URL", "http://localhost:5000")


def jprint(obj: Any, title: str) -> None:
    print(f"\n{title}")
    print("=" * len(title))
    print(json.dumps(obj, indent=2, sort_keys=True))


def get(url: str) -> Dict[str, Any]:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def post(url: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    response = requests.post(url, json=payload or {}, timeout=30)
    response.raise_for_status()
    return response.json()


def main() -> None:
    # 1) Inputs (config + anchors + prices)
    try:
        state = get(f"{API}/debug/market/state")
        jprint(state, "MARKET INPUT STATE")
    except Exception as exc:  # pragma: no cover - diagnostic script
        print(f"warn: /debug/market/state failed: {exc}")
        state = {}

    try:
        eval_preview = get(f"{API}/debug/market/eval")
        jprint(eval_preview, "PURE EVAL (WOULD-TRIGGER PREVIEW)")
    except Exception as exc:  # pragma: no cover - diagnostic script
        print(f"warn: /debug/market/eval failed: {exc}")

    # 2) Kick monitor once
    try:
        run = post(f"{API}/monitors/market_monitor")
        jprint(run, "RUN MARKET MONITOR ONCE")
    except Exception as exc:  # pragma: no cover - diagnostic script
        print(f"error: POST /monitors/market_monitor failed: {exc}")

    # brief pause for ledger write
    time.sleep(0.5)

    # 3) What the UI reads
    try:
        latest = get(f"{API}/api/market/latest")
        jprint(latest, "API /api/market/latest (UI payload)")
    except Exception as exc:  # pragma: no cover - diagnostic script
        print(f"error: GET /api/market/latest failed: {exc}")


if __name__ == "__main__":
    main()
