"""End-to-end market probe with HTTP + offline fallback.

HTTP path (preferred):
  1. GET /debug/market/state
  2. GET /debug/market/eval
  3. POST /monitors/market_monitor
  4. GET /api/market/latest

Offline fallback (if HTTP not reachable):
  * Reads DataLocker to dump cfg/anchors/prices and compute would-trigger preview.

Environment variables
---------------------
SONIC_API_URL (autodetects common ports if unset)
"""
from __future__ import annotations

import json
import os
import sys
import time
from importlib import import_module
from typing import Any, Dict, Iterable

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

    http_ok = True
    try:
        state = get(f"{base}/debug/market/state")
        jprint(state, "MARKET INPUT STATE (HTTP)")

        eval_preview = get(f"{base}/debug/market/eval")
        jprint(eval_preview, "PURE EVAL (HTTP WOULD-TRIGGER PREVIEW)")

        try:
            run = post(f"{base}/monitors/market_monitor")
            jprint(run, "RUN MARKET MONITOR ONCE (HTTP)")
        except Exception as exc:  # pragma: no cover - diagnostic script
            print(f"error: POST /monitors/market_monitor failed: {exc}")

        time.sleep(0.5)

        try:
            latest = get(f"{base}/api/market/latest")
            jprint(latest, "API /api/market/latest (HTTP UI PAYLOAD)")
        except Exception as exc:  # pragma: no cover - diagnostic script
            print(f"error: GET /api/market/latest failed: {exc}")
    except Exception as exc:  # pragma: no cover - diagnostic script
        http_ok = False
        print(f"HTTP not reachable ({exc}). Falling back to OFFLINE diagnostics.")

    if not http_ok:
        dl = _get_locker()
        cfg = _get_cfg(dl)
        assets = list(cfg["thresholds"].keys()) or ["SPX", "BTC", "ETH", "SOL"]
        prices = _get_latest_prices(dl, assets)
        jprint(
            {"cfg": cfg, "assets": assets, "prices": prices},
            "MARKET INPUT STATE (OFFLINE)",
        )
        eval_off = _eval(cfg, prices, assets)
        jprint(eval_off, "PURE EVAL (OFFLINE WOULD-TRIGGER PREVIEW)")


# ---------- helpers for offline fallback ----------
def _get_locker():
    """Lazy import to avoid hard dependency if only HTTP path is used."""

    dl_mod = import_module("backend.data.data_locker")
    core_mod = import_module("backend.core.core_constants")
    return dl_mod.DataLocker.get_instance(str(core_mod.MOTHER_DB_PATH))


def _get_cfg(dl) -> Dict[str, Any]:
    cfg = (dl.system.get_var("market_monitor") or {}) if getattr(dl, "system", None) else {}
    cfg.setdefault("thresholds", {})
    cfg.setdefault("anchors", {})
    cfg.setdefault("rearm_mode", "ladder")
    return cfg


def _get_latest_prices(dl, assets: Iterable[str]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for asset in assets:
        price_entry = dl.get_latest_price(asset) or {}
        if price_entry and price_entry.get("current_price") is not None:
            out[asset] = {
                "price": price_entry.get("current_price"),
                "ts": price_entry.get("ts") or price_entry.get("timestamp"),
                "source": price_entry.get("source") or "db",
            }
    return out


def _eval(cfg: Dict[str, Any], prices: Dict[str, Dict[str, Any]], assets: Iterable[str]) -> Dict[str, Any]:
    anchors = cfg.get("anchors") or {}
    thresholds = cfg.get("thresholds") or {}
    direction = cfg.get("direction") or {}

    detail: Dict[str, Dict[str, Any]] = {}
    for asset in assets:
        price = None if asset not in prices else prices[asset].get("price")
        anchor = anchors.get(asset)
        threshold = thresholds.get(asset)
        dirn = (direction.get(asset) or "Both") if isinstance(direction, dict) else "Both"

        if price is None or anchor is None or threshold is None:
            detail[asset] = {
                "price": price,
                "anchor": anchor,
                "threshold": threshold,
                "direction": dirn,
                "would_trigger": False,
                "reason": "missing price/anchor/threshold",
            }
            continue

        delta = price - anchor
        up = delta > 0
        dir_ok = (dirn == "Both") or (dirn == "Up" and up) or (dirn == "Down" and not up)
        would_trigger = bool(dir_ok and (abs(delta) >= float(threshold)))
        detail[asset] = {
            "price": price,
            "anchor": anchor,
            "delta": delta,
            "threshold": threshold,
            "direction": dirn,
            "dir_ok": dir_ok,
            "would_trigger": would_trigger,
        }

    return {
        "cfg_summary": {
            "rearm_mode": cfg.get("rearm_mode", "ladder"),
            "armed": cfg.get("armed", True),
        },
        "detail": detail,
    }


if __name__ == "__main__":
    main()
