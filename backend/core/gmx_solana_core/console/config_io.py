from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_JSON = Path.cwd() / "gmx_solana_console.json"

def load_json(path: Path = DEFAULT_JSON) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_json(data: Dict[str, Any], path: Path = DEFAULT_JSON) -> None:
    try:
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    except Exception as e:
        print(f"⚠️  Failed to write config JSON {path}: {e}")
