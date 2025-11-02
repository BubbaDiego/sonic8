from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict

DEFAULT_OUTBOX = Path(r"C:\\sonic7\\outbox")


def write_manifest(manifest: Dict[str, Any], suggested_name: str = "") -> Path:
    DEFAULT_OUTBOX.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    base = suggested_name or (manifest.get("action") or "tx")
    path = DEFAULT_OUTBOX / f"{ts}_{base}.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path
