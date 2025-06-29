#!/usr/bin/env python3
"""Simple connectivity test for Sonic1 backend.

Run this when the frontend appears to fetch no data. The script checks
basic API endpoints and reports their status codes and JSON validity.
"""
from __future__ import annotations

import os
import sys
from typing import Sequence

import requests


def check_endpoint(base: str, path: str) -> bool:
    url = f"{base.rstrip('/')}{path}"
    try:
        resp = requests.get(url, timeout=5)
        print(f"{url} -> {resp.status_code}")
        if resp.ok:
            try:
                data = resp.json()
                keys = list(data.keys())[:5] if isinstance(data, dict) else None
                if keys:
                    print(f"  JSON keys: {keys}")
            except Exception:
                print("  Response not valid JSON")
        else:
            print(f"  ERROR: {resp.text[:200]}")
        return resp.ok
    except requests.RequestException as exc:
        print(f"{url} -> ERROR: {exc}")
        return False


def main(argv: Sequence[str] | None = None) -> int:
    base_url = os.getenv("SONIC_BACKEND_URL", "http://localhost:5000")
    endpoints = ["/api/status", "/positions"]
    print(f"Checking backend at {base_url}")
    success = True
    for ep in endpoints:
        if not check_endpoint(base_url, ep):
            success = False
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
