#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discover the canonical Position PDA by trying the common seed orders.

Usage examples (Windows PowerShell/CMD friendly):

  # Minimal: owner + pool + "Right:" (from Perps ConstraintSeeds log) to find the match
  python backend/scripts/discover_position_pda.py ^
    --owner CofTLEqPUXscsigdvP8YWkRTDmCQ6W7GKBVKRsZ6UvLn ^
    --pool  5BUwFW4nRbftYTDMbgxykoFWqWHPzahFSNAaaaJtVKsq ^
    --expect 8oWD2JvGDiNU4jfCKEuVm3M6amCz11k36La2T2PJ2gvq

  # Include one or more custody pubkeys if you want the tool to try custody-aware recipes
  python backend/scripts/discover_position_pda.py ^
    --owner <OWNER> ^
    --pool  <POOL> ^
    --custodies <CUSTODY1>,<CUSTODY2> ^
    --expect <RIGHT_FROM_LOG>

Notes:
- Program defaults to Jupiter Perps mainnet program id:
    PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu
- The tool tries both 'position' and 'Position' prefixes and a small set of
  plausible seed orders that cover 99% of perps-style PDAs.
- If you know the market custody (e.g., SOL custody), include it via --custodies
  to try [pool, marketCustody, owner] etc.
"""

import argparse
import sys
from typing import List, Tuple

try:
    from solana.publickey import PublicKey
except Exception:
    print("This script requires the 'solana' package.\n"
          "Install it in your venv:  pip install solana", file=sys.stderr)
    sys.exit(1)

PERPS_PROGRAM_DEFAULT = "PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu"

B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def is_base58(s: str) -> bool:
    return len(s) >= 32 and all(c in B58 for c in s.strip())

def parse_pk(label: str, v: str) -> PublicKey:
    v = v.strip()
    if not is_base58(v):
        raise ValueError(f"Invalid base58 for {label}: {v}")
    return PublicKey(v)

def pda(program: PublicKey, seeds: List[bytes]) -> Tuple[PublicKey, int]:
    return PublicKey.find_program_address(seeds, program)

def main() -> int:
    ap = argparse.ArgumentParser(description="Discover Position PDA by trying common seed orders.")
    ap.add_argument("--program", default=PERPS_PROGRAM_DEFAULT, help="Perps program id (default: mainnet)")
    ap.add_argument("--owner", required=True, help="Owner pubkey (your wallet)")
    ap.add_argument("--pool", required=True,  help="Pool pubkey (from logs)")
    ap.add_argument("--custodies", default="", help="Comma-separated custody pubkeys to try (optional)")
    ap.add_argument("--expect", default="", help="Expected (Right:) position PDA from Perps log (optional)")
    args = ap.parse_args()

    try:
        program = parse_pk("program", args.program)
        owner   = parse_pk("owner", args.owner)
        pool    = parse_pk("pool",  args.pool)
        expect  = parse_pk("expect", args.expect) if args.expect else None
        custodies: List[PublicKey] = []
        if args.custodies.strip():
            for s in args.custodies.split(","):
                s = s.strip()
                if s:
                    custodies.append(parse_pk("custody", s))
    except ValueError as e:
        print(f"✖ {e}", file=sys.stderr)
        return 2

    print("program =", program)
    print("owner   =", owner)
    print("pool    =", pool)
    if custodies:
        print("custodies =", ", ".join(str(c) for c in custodies))
    if expect:
        print("expect  =", expect)

    prefixes = [b"position", b"Position"]

    # Seed orders to try:
    #  - Two-part: (owner,pool) and (pool,owner)
    #  - Three-part variants with one custody sprinkled in (pool,mc,owner) etc.
    def uniq_pubkeys(lst: List[PublicKey]) -> List[PublicKey]:
        seen = set(); out: List[PublicKey] = []
        for pk in lst:
            s = str(pk)
            if s not in seen:
                seen.add(s); out.append(pk)
        return out

    combos: List[Tuple[str, List[PublicKey]]] = []
    combos.append(("owner,pool", [owner, pool]))
    combos.append(("pool,owner", [pool, owner]))

    for c in custodies[:4]:
        combos.append(("pool,mc,owner",  uniq_pubkeys([pool, c, owner])))
        combos.append(("owner,pool,mc",  uniq_pubkeys([owner, pool, c])))
        combos.append(("mc,pool,owner",  uniq_pubkeys([c, pool, owner])))
        combos.append(("pool,owner,mc",  uniq_pubkeys([pool, owner, c])))

    hits = 0
    print("\nTrying seed recipes…\n")
    for pfx in prefixes:
        for label, parts in combos:
            seeds = [pfx] + [pk.to_bytes() for pk in parts]
            addr, bump = pda(program, seeds)
            tag = ""
            if expect and addr == expect:
                tag = "  <= MATCH expected"
                hits += 1
            print(f"{pfx.decode()} :: [{label}] => {addr}  bump={bump}{tag}")

    if expect and hits == 0:
        print("\nNo match for expected. Try adding the market custody to --custodies "
              "(e.g., the SOL custody for SOL-long), or share the 'Right:' address "
              "and we can extend the recipes.")
    elif expect and hits > 0:
        print(f"\n✓ Found {hits} matching recipe(s). Use the one that matched in your client.")

    return 0

if __name__ == "__main__":
    sys.exit(main())
