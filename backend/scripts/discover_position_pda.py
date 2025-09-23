#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Self-executable Position PDA discoverer (no CLI args).
Edit the CONFIG below, then run:
    python backend/scripts/discover_position_pda.py
It will try many seed recipes and print any that MATCH your expected PDA.
"""

# =========================
# ======  CONFIG  =========
# =========================

PROGRAM      = "PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu"   # perps program id
OWNER        = "CofTLEqPUXscsigdvP8YWkRTDmCQ6W7GKBVKRsZ6UvLn"  # your wallet
POOL         = "5BUwFW4nRbftYTDMbgxykoFWqWHPzahFSNAaaaJtVKsq"  # pool
PERPETUALS   = "H4ND9aYttUVLFmNypZqLjZ52FYiGvdEB45GmwNoKEjTj"  # singleton you printed
# Custodies (add both SOL market custody and USDC custody you printed)
CUSTODIES    = [
    "7xS2gz2bTp3FwCC7KnJvUWTEU9TYcczu6VhJYkgiwdz",  # SOL market custody (mint So111…)
    "G1bjKKQxQwbBrHeik3C9MRXhHsLlf7XgCSisykU46Eza",  # USDC custody (mint EPjF…)
]
# Expected PDA from the Perps “Right:” line (so we can flag a match)
EXPECT       = "8oWD2JvGDiNU4jfCKEuVm3M6amCz11k36La2T2PJ2gvq"

# =========================
# =====  IMPLEMENT  =======
# =========================
from typing import List, Tuple
# Prefer solders (solana-py ≥0.30), fall back to legacy solana
try:
    from solders.pubkey import Pubkey as _Pubkey
    API="solders"
    def _pk(s:str)->_Pubkey: return _Pubkey.from_string(s)
    def _pda(seeds:List[bytes], prog:_Pubkey)->Tuple[_Pubkey,int]: return _Pubkey.find_program_address(seeds, prog)
    def _b(pk:_Pubkey)->bytes: return bytes(pk)
    def _s(pk:_Pubkey)->str:   return str(pk)
except Exception:
    from solana.publickey import PublicKey as _Pubkey
    API="legacy"
    def _pk(s:str)->_Pubkey: return _Pubkey(s)
    def _pda(seeds:List[bytes], prog:_Pubkey)->Tuple[_Pubkey,int]: return _Pubkey.find_program_address(seeds, prog)
    def _b(pk:_Pubkey)->bytes: return bytes(pk)
    def _s(pk:_Pubkey)->str:   return str(pk)

B58 = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
def sanitize(s:str)->str: return "".join(ch for ch in s.strip() if ch in B58)

def parse(label:str, s:str)->_Pubkey:
    raw=s; s=sanitize(s)
    try:
        pk=_pk(s)
        if raw!=s: print(f"⚠ sanitized {label}: {raw!r} -> {s!r} (len {len(s)})")
        return pk
    except Exception as e:
        raise ValueError(f"Invalid {label}: {raw!r} (after sanitize {s!r})") from e

def uniq(lst:List[_Pubkey])->List[_Pubkey]:
    seen=set(); out=[]
    for x in lst:
        sx=_s(x)
        if sx not in seen:
            seen.add(sx); out.append(x)
    return out

def main()->int:
    prog = parse("program", PROGRAM)
    owner= parse("owner",   OWNER)
    pool = parse("pool",    POOL)
    perp = parse("perpetuals", PERPETUALS)
    custs=[parse("custody", c) for c in CUSTODIES if c.strip()]
    expect=_pk(sanitize(EXPECT)) if EXPECT.strip() else None

    print(f"(API={API})")
    print("program   =", _s(prog))
    print("owner     =", _s(owner))
    print("pool      =", _s(pool))
    print("perpetuals=", _s(perp))
    if custs: print("custodies =", ", ".join(_s(c) for c in custs))
    if expect: print("expect    =", _s(expect))

    prefixes=[b"position", b"Position"]
    parts_base=[owner, pool, perp] + custs
    parts = uniq(parts_base)

    # generate permutations of length 2..4 (owner/pool/perpetuals/custodies)
    from itertools import permutations
    recipes=[]
    for L in (2,3,4):
        for combo in permutations(parts, L):
            # must include at least owner and pool
            have_owner=any(_s(x)==_s(owner) for x in combo)
            have_pool =any(_s(x)==_s(pool)  for x in combo)
            if not (have_owner and have_pool): continue
            recipes.append(list(combo))

    hits=0
    print("\nTrying seed recipes…\n")
    for pfx in prefixes:
        for combo in recipes:
            seeds=[pfx]+[_b(x) for x in combo]
            addr,bump=_pda(seeds, prog)
            tag=""
            if expect and _s(addr)==_s(expect):
                tag="  <= MATCH expected"; hits+=1
            label=",".join((_s(x) for x in combo))  # long, but we’ll also show short form:
            short=",".join((_s(x)[:4] for x in combo))
            print(f"{pfx.decode()} :: [{short}] => {_s(addr)}  bump={bump}{tag}")
            if tag: print(f"FULL ORDER: {pfx.decode()} :: [{label}]")

    if expect and hits==0:
        print("\nNo match found for EXPECT. Add/remove a custody, or double-check EXPECT from Perps log.")
    elif expect:
        print(f"\n✓ Found {hits} matching recipe(s). Use the FULL ORDER printed above in your client.")
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(f"✖ {e}")
        raise
