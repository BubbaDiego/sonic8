"""
IDL loader helper (Phase S-2).

Responsibilities:
- load Anchor IDL JSON from disk or package
- validate required program ids in config
"""
import json
from typing import Dict, Any

def load_idl(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
