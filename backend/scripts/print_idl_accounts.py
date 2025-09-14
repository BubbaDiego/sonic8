#!/usr/bin/env python3
"""
Print the accounts array (and args) for a given instruction from a Jupiter Perps IDL JSON.

Run as-is:  python print_idl_accounts.py

If your IDL is in a different path, edit IDL_PATH below.
You can add/remove names in INSTR_NAMES; the script does a case-insensitive match and
also supports substring search (so 'createDecreasePositionRequest2' or 'decreasePositionRequest2' both hit).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

# ========= CONFIG =========
IDL_PATH = r"C:\sonic5\backend\services\perps\idl\jupiter_perpetuals.json"

# Try these names in order (case-insensitive; substring ok).
INSTR_NAMES = [
    "createDecreasePositionRequest2",
    "createDecreasePositionRequest",
    "createDecreasePositionMarketRequest",
]
# ==========================


def load_idl(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"IDL not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_instruction(idl: Dict[str, Any], names: List[str]) -> Optional[Dict[str, Any]]:
    instrs = idl.get("instructions") or idl.get("ix") or []
    # normalize to list of dicts
    if not isinstance(instrs, list):
        return None

    # case-insensitive matching; also allow substring
    lower_names = [n.lower() for n in names]
    for cand in lower_names:
        for ix in instrs:
            nm = (ix.get("name") or "").lower()
            if nm == cand or cand in nm:
                return ix
    return None


def pretty_accounts(ix: Dict[str, Any]) -> str:
    lines = []
    accs = ix.get("accounts") or []
    if not isinstance(accs, list):
        return "  (no accounts listed)"
    max_name = max((len(a.get("name","")) for a in accs), default=4)
    lines.append(f"ACCOUNTS ({len(accs)}):")
    for i, a in enumerate(accs, 1):
        name = a.get("name", "")
        is_mut = a.get("isMut", False)
        is_signer = a.get("isSigner", False)
        is_optional = a.get("isOptional", False)
        lines.append(f"  {i:>2}. {name.ljust(max_name)}  "
                     f"isMut={str(is_mut):5}  isSigner={str(is_signer):5}"
                     + (f"  isOptional={str(is_optional):5}" if is_optional else ""))
    return "\n".join(lines)


def pretty_args(ix: Dict[str, Any]) -> str:
    args = ix.get("args") or []
    if not args:
        return "ARGS: (none)"
    lines = ["ARGS:"]
    for a in args:
        nm = a.get("name", "?")
        ty = a.get("type", "?")
        lines.append(f"  - {nm}: {json.dumps(ty)}")
    return "\n".join(lines)


def main():
    print("== IDL Instruction Accounts Printer ==")
    print(f"IDL: {IDL_PATH}\n")
    idl = load_idl(IDL_PATH)

    ix = find_instruction(idl, INSTR_NAMES)
    if not ix:
        # help the user see what's available
        names = [i.get("name","") for i in (idl.get("instructions") or [])]
        print("Instruction not found. Tried names:")
        for n in INSTR_NAMES:
            print(f"  - {n}")
        print("\nAvailable instruction names in this IDL (first 50 shown):")
        for nm in names[:50]:
            print(f"  - {nm}")
        return

    nm = ix.get("name", "<unknown>")
    print(f"INSTRUCTION: {nm}\n")
    print(pretty_accounts(ix))
    print()
    print(pretty_args(ix))
    print("\nDone.")


if __name__ == "__main__":
    main()
