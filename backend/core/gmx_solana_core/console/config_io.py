from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict

DEFAULT_JSON = Path(os.environ.get("GMSOL_CONSOLE_JSON", r"C:\\sonic7\\gmx_solana_console.json"))


def load_json(p: Path = DEFAULT_JSON) -> Dict[str, Any]:
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_json(obj: Dict[str, Any], p: Path = DEFAULT_JSON) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")
