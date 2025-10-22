from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = Path(os.environ.get("SONIC_MONITOR_JSON", ROOT / "backend" / "config" / "sonic_monitor_config.json"))


def atomic_write(p: Path, data: dict):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(p.parent), delete=False) as tmp:
        json.dump(data, tmp, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        name = tmp.name
    os.replace(name, str(p))


def main() -> int:
    if not PATH.exists():
        print("Missing:", PATH)
        return 2

    try:
        raw = PATH.read_text(encoding="utf-8")
        cfg = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        print("Invalid JSON:", exc)
        return 3

    cfg.setdefault("monitor", {}).setdefault("enabled", {})
    cfg.setdefault("channels", {})
    cfg.setdefault("liquid", {}).setdefault("thresholds", {})
    prof = cfg.setdefault("profit", {})
    prof.setdefault("snooze_seconds", 600)
    prof.setdefault("position_usd", 0)
    prof.setdefault("portfolio_usd", 0)

    atomic_write(PATH, cfg)
    print("Repaired:", PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
