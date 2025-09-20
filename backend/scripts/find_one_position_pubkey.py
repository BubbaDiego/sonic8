#!/usr/bin/env python3
# Find ONE Position account for your wallet by scanning Helius getProgramAccountsV2 (paged)
# It looks for your OWNER pubkey bytes ANYWHERE in each account's raw data.

from __future__ import annotations

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

import base64
import json
import os
import random
import time
from typing import Any, Optional

import requests

from backend.config.rpc import helius_url, redacted

# ---- CONFIG (edit if needed) ----
OWNER_PUBKEY   = "V8iveiirFvX7m7psPHWBJW85xPk1ZB6U4Ep9GUV2THW"
PROGRAM_ID     = "PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu"  # verified from pool owner
RPC_URL        = os.getenv("RPC_URL") or helius_url()

PAGE_LIMIT     = 800    # accounts per page (tune if needed)
MAX_PAGES      = 550     # how many pages to scan before giving up
BACKOFF_BASE   = 0.5
# -------------------------------

# base58 decode (tiny, no deps)
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_IDX = {ch:i for i,ch in enumerate(_B58)}
def b58dec(s: str) -> bytes:
    n=0
    for ch in s.strip():
        if ch not in _B58_IDX: raise ValueError(f"bad base58 char: {ch}")
        n=n*58+_B58_IDX[ch]
    full=n.to_bytes((n.bit_length()+7)//8, "big") if n else b"\x00"
    leading=0
    for ch in s:
        if ch=="1": leading+=1
        else: break
    return (b"\x00"*leading)+full.lstrip(b"\x00")

OWNER_BYTES = b58dec(OWNER_PUBKEY)

def rpc(method: str, params: Any, retries: int = 6, base_delay: float = BACKOFF_BASE):
    last=None
    for i in range(retries):
        try:
            r = requests.post(RPC_URL, json={"jsonrpc":"2.0","id":1,"method":method,"params":params}, timeout=30)
            if r.status_code in (429,502,503,504):
                time.sleep(base_delay*(2**i)+random.uniform(0,0.25)); continue
            r.raise_for_status()
            data = r.json()
            if data.get("error"):
                msg = str(data["error"])
                if "Too many" in msg or "rate" in msg.lower():
                    time.sleep(base_delay*(2**i)+random.uniform(0,0.25)); continue
                raise RuntimeError(msg)
            return data.get("result")
        except Exception as e:
            last=e; time.sleep(base_delay*(2**i)+random.uniform(0,0.25))
    raise RuntimeError(f"RPC failed: {last}")

def raw_from_data(data: Any) -> Optional[bytes]:
    try:
        if isinstance(data, list) and data and isinstance(data[0], str):
            return base64.b64decode(data[0])
        if isinstance(data, dict) and isinstance(data.get("encoded"), str):
            return base64.b64decode(data["encoded"])
    except Exception:
        return None
    return None

def main():
    print("== Find ONE Position pubkey ==")
    print(f"RPC:     {redacted(RPC_URL)}")
    print(f"Program: {PROGRAM_ID}")
    print(f"Owner:   {OWNER_PUBKEY}\n")

    pagination_key = None
    for page in range(1, MAX_PAGES+1):
        params = {"encoding":"base64", "limit": PAGE_LIMIT}
        if pagination_key: params["paginationKey"] = pagination_key
        res = rpc("getProgramAccountsV2", [PROGRAM_ID, params]) or {}
        accs = res.get("accounts") if isinstance(res, dict) else []
        pagination_key = res.get("paginationKey") if isinstance(res, dict) else None

        if not isinstance(accs, list) or not accs:
            print("No more accounts. Giving up."); return

        print(f"Scanning page {page} (accounts: {len(accs)})…")
        for it in accs:
            if not isinstance(it, dict): continue
            pk = it.get("pubkey")
            acct = it.get("account") or {}
            data = acct.get("data")
            raw = raw_from_data(data)
            if not isinstance(raw, (bytes, bytearray)):
                # Try refetch full bytes using space length if present
                space = acct.get("space")
                if isinstance(space, int) and space > 0:
                    try:
                        full = rpc("getAccountInfo", [pk, {"encoding":"base64","commitment":"confirmed","dataSlice":{"offset":0,"length":space}}]) or {}
                        v = full.get("value") if isinstance(full, dict) else None
                        raw = raw_from_data(v.get("data")) if isinstance(v, dict) else None
                    except Exception:
                        raw = None
            if isinstance(raw, (bytes, bytearray)) and OWNER_BYTES in raw:
                print("\nFOUND position account for owner:")
                print("POSITION_PUBKEY =", pk)
                print("\n→ Paste that into your main script’s KNOWN_POSITION_PUBKEY, save, run again.")
                return

        if not pagination_key:
            print("Reached last page without finding owner bytes.")
            break

    print("\nNo match yet. You can increase MAX_PAGES or PAGE_LIMIT at the top and run again.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
