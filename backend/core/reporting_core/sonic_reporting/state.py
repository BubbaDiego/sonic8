# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Dict, Set

_PRINT_MEMO: Dict[str, Set[str]] = {}

def cycle_key(csum: dict | None) -> str:
    if isinstance(csum, dict):
        if csum.get("cycle_id"):
            return str(csum["cycle_id"])
        ts = (csum.get("positions") or {}).get("ts") or (csum.get("prices") or {}).get("ts") or ""
        return f"ts:{ts}"
    return "global"

def once(flag: str, csum: dict | None) -> bool:
    k = cycle_key(csum)
    s = _PRINT_MEMO.setdefault(k, set())
    if flag in s:
        return False
    # rotate keys, keep few
    if len(_PRINT_MEMO) > 4:
        for key in list(_PRINT_MEMO.keys())[:-2]:
            _PRINT_MEMO.pop(key, None)
    s.add(flag)
    return True
