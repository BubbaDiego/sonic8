#!/usr/bin/env python3
"""
Print PDA seed metadata (if present) for the accounts in the 'createDecreasePositionRequest2'
instruction from your Jupiter Perps IDL JSON.

Run as-is. If your IDL is elsewhere, change IDL_PATH.
"""

from __future__ import annotations

import json, os
from typing import Any, Dict, List, Optional

# --- CONFIG ---
IDL_PATH = r"C:\sonic5\backend\services\perps\idl\jupiter_perpetuals.json"
INSTR_NAME = "createDecreasePositionRequest2"
# -------------


def load_idl(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"IDL not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_instruction(idl: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    instrs = idl.get("instructions") or []
    name_l = name.lower()
    for ix in instrs:
        nm = (ix.get("name") or "").lower()
        if nm == name_l:
            return ix
    return None


def fmt_seed(s: Dict[str, Any]) -> str:
    # Anchor IDL pda.seed can have kinds: "bytes", "const", "arg", "account", "programId", "sysvar"
    # We'll print them in a helpful way.
    kind = next(iter(s.keys()), "?")
    val  = s.get(kind)
    return f"{kind}: {json.dumps(val)}"


def print_pda_info_for_accounts(idl: Dict[str, Any], ix: Dict[str, Any]) -> None:
    print(f"INSTRUCTION: {ix.get('name')}\n")
    accs = ix.get("accounts") or []
    if not isinstance(accs, list):
        print("  (no accounts listed)")
        return

    # Some IDLs place 'pda' meta on the instruction account entry;
    # Others keep it on the global 'accounts' schema definition.
    # We'll try both: per-ix entry, and fallback by name in idl['accounts'].
    global_accounts = {a.get("name"): a for a in (idl.get("accounts") or [])}

    for i, a in enumerate(accs, 1):
        nm = a.get("name")
        print(f"{i:>2}. {nm}")
        pda = a.get("pda")
        printed = False
        if isinstance(pda, dict):
            seeds = pda.get("seeds") or []
            if seeds:
                print("    pda.seeds (from instruction):")
                for s in seeds:
                    print("     •", fmt_seed(s))
                printed = True

        # fallback to global account schema
        if not printed and nm in global_accounts:
            ga = global_accounts[nm]
            pda2 = ga.get("pda")
            seeds2 = (pda2 or {}).get("seeds") if isinstance(pda2, dict) else None
            if seeds2:
                print("    pda.seeds (from account schema):")
                for s in seeds2:
                    print("     •", fmt_seed(s))
                printed = True

        if not printed:
            print("    (no pda.seeds metadata visible in IDL for this account)")
    print("\nARGS:")
    for arg in ix.get("args") or []:
        print("  -", arg.get("name"), ":", json.dumps(arg.get("type")))


def main():
    print("== IDL PDA Seed Printer ==")
    print(f"IDL: {IDL_PATH}")
    idl = load_idl(IDL_PATH)
    ix = find_instruction(idl, INSTR_NAME)
    if not ix:
        print(f"Instruction '{INSTR_NAME}' not found. Available:")
        for nm in [i.get("name") for i in (idl.get("instructions") or [])][:50]:
            print("  -", nm)
        return
    print_pda_info_for_accounts(idl, ix)
    print("\nDone.")


if __name__ == "__main__":
    main()
