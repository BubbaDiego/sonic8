#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discover the canonical Position PDA by trying the common seed orders.

Examples:
  python backend/scripts/discover_position_pda.py ^
    --owner CofTLEqPUXscsigdvP8YWkRTDmCQ6W7GKBVKRsZ6UvLn ^
    --pool  5BUwFW4nRbftYTDMbgxykoFWqWHPzahFSNAaaaJtVKsq ^
    --expect 8oWD2JvGDiNU4jfCKEuVm3M6amCz11k36La2T2PJ2gvq

  python backend/scripts/discover_position_pda.py ^
    --owner <OWNER> --pool <POOL> --custodies <SOL_CUSTODY>,<OTHER> --expect <RIGHT_PDA>

Compatible with solana-py ≥0.30 (solders) and older solana-py (legacy).
"""

import argparse
import sys
from typing import List, Tuple

# --- PublicKey compat (solders first, then legacy solana.py) -----------------
try:
    from solders.pubkey import Pubkey as _Pubkey

    def PublicKey(v: str) -> _Pubkey:
        return _Pubkey.from_string(v.strip())

    def pubkey_to_bytes(pk: _Pubkey) -> bytes: return bytes(pk)
    def pubkey_to_str(pk: _Pubkey) -> str:     return str(pk)
    def find_program_address(seeds, program):   return _Pubkey.find_program_address(seeds, program)
    API = "solders"

except Exception:
    from solana.publickey import PublicKey as _Pubkey  # legacy

    def PublicKey(v: str) -> _Pubkey:          return _Pubkey(v.strip())
    def pubkey_to_bytes(pk: _Pubkey) -> bytes: return bytes(pk)
    def pubkey_to_str(pk: _Pubkey) -> str:     return str(pk)
    def find_program_address(seeds, program):   return _Pubkey.find_program_address(seeds, program)
    API = "legacy"

PERPS_PROGRAM_DEFAULT = "PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu"

def parse_pk(label: str, v: str):
    try:
        return PublicKey(v)
    except Exception as e:
        raise ValueError(f"Invalid pubkey for {label}: {v}") from e

def pda(program, seeds: List[bytes]):
    addr, bump = find_program_address(seeds, program)
    return addr, bump

def main() -> int:
    ap = argparse.ArgumentParser(description="Discover Position PDA by trying common seed orders.")
    ap.add_argument("--program", default=PERPS_PROGRAM_DEFAULT, help="Perps program id (default mainnet)")
    ap.add_argument("--owner",   required=True, help="Owner pubkey")
    ap.add_argument("--pool",    required=True, help="Pool pubkey")
    ap.add_argument("--custodies", default="", help="Comma-separated custody pubkeys (optional)")
    ap.add_argument("--expect",  default="", help="Expected (Right:) PDA from Perps log (optional)")
    args = ap.parse_args()

    try:
        program = parse_pk("program", args.program)
        owner   = parse_pk("owner",   args.owner)
        pool    = parse_pk("pool",    args.pool)
        expect  = parse_pk("expect",  args.expect) if args.expect else None
        custodies: List = []
        if args.custodies.strip():
            for s in args.custodies.split(","):
                s = s.strip()
                if s:
                    custodies.append(parse_pk("custody", s))
    except ValueError as e:
        print(f"✖ {e}", file=sys.stderr)
        return 2

    print(f"(API={API})")
    print("program =", pubkey_to_str(program))
    print("owner   =", pubkey_to_str(owner))
    print("pool    =", pubkey_to_str(pool))
    if custodies:
        print("custodies =", ", ".join(pubkey_to_str(c) for c in custodies))
    if expect:
        print("expect  =", pubkey_to_str(expect))

    prefixes = [b"position", b"Position"]

    def uniq(lst: List) -> List:
        seen = set(); out: List = []
        for pk in lst:
            s = pubkey_to_str(pk)
            if s not in seen:
                seen.add(s); out.append(pk)
        return out

    combos: List[Tuple[str, List]] = []
    combos.append(("owner,pool", [owner, pool]))
    combos.append(("pool,owner", [pool, owner]))

    for c in custodies[:4]:
        combos.append(("pool,mc,owner",  uniq([pool, c, owner])))
        combos.append(("owner,pool,mc",  uniq([owner, pool, c])))
        combos.append(("mc,pool,owner",  uniq([c, pool, owner])))
        combos.append(("pool,owner,mc",  uniq([pool, owner, c])))

    hits = 0
    print("\nTrying seed recipes…\n")
    for pfx in prefixes:
        for label, parts in combos:
            seeds = [pfx] + [pubkey_to_bytes(pk) for pk in parts]
            addr, bump = pda(program, seeds)
            tag = ""
            if expect and pubkey_to_str(addr) == pubkey_to_str(expect):
                tag = "  <= MATCH expected"
                hits += 1
            print(f"{pfx.decode()} :: [{label}] => {pubkey_to_str(addr)}  bump={bump}{tag}")

    if expect and hits == 0:
        print("\nNo match for expected. Try including the market custody for your market via --custodies.")
    elif expect and hits > 0:
        print(f"\n✓ Found {hits} matching recipe(s). Use the one that matched in your client.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
