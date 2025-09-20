#!/usr/bin/env python3
# Jupiter Perps — standalone console tool (no CLI args)
# - Uses Helius getProgramAccountsV2 (object shape) everywhere
# - Filters YOUR positions via memcmp(disc@0) + memcmp(owner@offset)
# - Optional decode (Side / Size / Entry / Mark / est. PnL) if IDL_PATH set + anchorpy installed
#
# Run:  python jup_perps_positions.py
# Notes:
# * For decoding, you need a canonical Anchor JSON IDL (pure JSON; no BN()/PublicKey()).
# * This script will auto-detect the correct IDL account name by matching discriminators.

from __future__ import annotations

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

import base64
import hashlib
import json
import os
import random
import time
from collections import Counter
from typing import Any, Dict, List, Optional

import requests

from backend.config.rpc import helius_url, redacted


# ===========================
# CONFIG — EDIT IF YOU WANT
# ===========================
OWNER_PUBKEY   = "CzRzD26vfaSgNVxM93Hpy2VHtiaLmQrVNCRbSWd1ikR7"
PROGRAM_ID     = "PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu"  # verified via pool owner
RPC_URL        = os.getenv("RPC_URL") or helius_url()
print(f"[rpc] using {redacted(RPC_URL)}")

# Known Position discriminator & owner offset (derived earlier)
POSITION_DISC_HEX = "aabc8fe47a40f7d0"
OWNER_OFFSET      = 8

# Optional: canonical Anchor JSON IDL path → enables decode if anchorpy is installed
IDL_PATH          = ""  # e.g. r"C:\sonic5\backend\services\perps\idl\jupiter_perpetuals.json"

# Fetch/print
LIMIT_POS         = 100  # how many positions to list
SHOW_MARKETS      = True # small disc inventory from first page
# ===========================


# -------- base58 helpers (tiny) --------
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_IDX = {ch:i for i,ch in enumerate(_B58)}
def b58enc(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    s = _B58[0] if n == 0 else ""
    out=[]
    while n:
        n,r = divmod(n,58)
        out.append(_B58[r])
    if out: s += "".join(reversed(out))
    z=0
    for ch in b:
        if ch==0: z+=1
        else: break
    return (_B58[0]*z) + s

def b58dec(s: str) -> bytes:
    n=0
    for ch in s.strip():
        if ch not in _B58_IDX: raise ValueError(f"bad base58 char: {ch}")
        n=n*58 + _B58_IDX[ch]
    full = n.to_bytes((n.bit_length()+7)//8, "big") if n else b"\x00"
    leading=0
    for ch in s:
        if ch=="1": leading+=1
        else: break
    return (b"\x00"*leading) + full.lstrip(b"\x00")

OWNER_BYTES = b58dec(OWNER_PUBKEY)
POSITION_DISC = bytes.fromhex(POSITION_DISC_HEX)


# -------- robust Helius JSON-RPC with backoff --------
def rpc(method: str, params: Any, retries: int = 6, base_delay: float = 0.5) -> Any:
    last=None
    for i in range(retries):
        try:
            r = requests.post(RPC_URL, json={"jsonrpc":"2.0","id":1,"method":method,"params":params}, timeout=30)
            if r.status_code in (429, 502, 503, 504):
                time.sleep(base_delay*(2**i) + random.uniform(0,0.25)); continue
            r.raise_for_status()
            data = r.json()
            if data.get("error"):
                msg = str(data["error"])
                if "Too many" in msg or "rate" in msg.lower():
                    time.sleep(base_delay*(2**i) + random.uniform(0,0.25)); continue
                raise RuntimeError(f"RPC error: {msg}")
            return data.get("result")
        except Exception as e:
            last=e
            time.sleep(base_delay*(2**i) + random.uniform(0,0.25))
    raise RuntimeError(f"RPC failed: {last}")


# -------- raw/b64 helpers --------
def raw_from_data(data: Any) -> Optional[bytes]:
    try:
        if isinstance(data, list) and data and isinstance(data[0], str):
            return base64.b64decode(data[0])
        if isinstance(data, dict) and isinstance(data.get("encoded"), str):
            return base64.b64decode(data["encoded"])
    except Exception:
        return None
    return None


# -------- V2 helpers (object shape: {"accounts":[...],"paginationKey":...}) --------
def program_has_any_accounts_v2(pid: str) -> bool:
    try:
        res = rpc("getProgramAccountsV2", [pid, {"encoding":"base64","limit":1}]) or {}
        accs = res.get("accounts") if isinstance(res, dict) else None
        return isinstance(accs, list) and len(accs) > 0
    except Exception:
        return False

def list_positions_v2(pid: str, disc: bytes, owner: str, off: int, limit: int) -> List[str]:
    params = {"encoding":"base64","limit":limit, "filters":[
        {"memcmp":{"offset":0,"bytes": b58enc(disc)}},
        {"memcmp":{"offset":int(off),"bytes": owner}}
    ]}
    res = rpc("getProgramAccountsV2", [pid, params]) or {}
    accs = res.get("accounts") if isinstance(res,dict) else []
    pubs=[]
    if isinstance(accs, list):
        for it in accs:
            if isinstance(it, dict) and isinstance(it.get("pubkey"), str):
                pubs.append(it["pubkey"])
    return pubs


# -------- optional decode (anchorpy + IDL) --------
def try_decode_positions(idl_path: str, disc: bytes, pubs: List[str]) -> None:
    try:
        from anchorpy import Idl
        from anchorpy.coder.accounts import AccountCoder
        with open(idl_path,"r",encoding="utf-8") as f:
            idl_json = json.load(f)
        coder = AccountCoder(Idl.from_json(idl_json))
    except Exception as e:
        print(f"\nNOTE: cannot decode (anchorpy/IDL): {e}\n"); return

    # pick the correct IDL account name by matching discriminator
    def disc_for_name(name: str) -> bytes:
        return hashlib.sha256(f"account:{name}".encode("utf-8")).digest()[:8]
    idl_accounts = [a.get("name") for a in (idl_json.get("accounts") or []) if isinstance(a, dict)]
    account_name = None
    for name in idl_accounts:
        try:
            if disc_for_name(name) == disc:
                account_name = name
                break
        except Exception:
            continue
    if not account_name:
        account_name = "Position"  # fallback guess
        print(f"NOTE: could not match IDL account by discriminator. Trying '{account_name}'.")

    # minimal field extractors
    def raw_from_multi(v: dict) -> Optional[bytes]:
        return raw_from_data(v.get("data", {})) if isinstance(v, dict) else None
    def _num(x):
        try:
            if x is None: return None
            if isinstance(x,(int,float)): return float(x)
            if isinstance(x,str):
                s=x.strip()
                if s.lower().startswith("0x"): return float(int(s,16))
                return float(s)
            v=getattr(x,"value",None); return float(v) if v is not None else None
        except Exception: return None
    def _q64(v):
        n=_num(v);
        if n is None: return None
        return n/(2**64) if n>1e9 else n
    def _decs(d):
        for k in ("decimals","baseDecimals","assetDecimals"):
            if k in d:
                try: return int(d[k])
                except Exception: pass
        return 9
    def extract_fields(d: Dict[str,Any]):
        side=None
        if "isLong" in d: side="LONG" if bool(d["isLong"]) else "SHORT"
        elif "side" in d:
            try: side="LONG" if int(d["side"])>0 else "SHORT"
            except Exception:
                s=str(d["side"]).lower(); side="LONG" if "long" in s else "SHORT" if "short" in s else None
        size_atoms=None
        for k in ("size","baseSize","qty","quantity","positionSize"):
            if k in d:
                size_atoms=_num(d[k]);
                if size_atoms is not None: break
        decs=_decs(d); size_ui=size_atoms/(10**decs) if size_atoms is not None else None
        entry=None
        for k in ("entryPrice","avgEntryPrice","openPrice"):
            if k in d:
                entry=_num(d[k]);
                if entry is not None: break
        if entry is None and "entryPriceX64" in d: entry=_q64(d["entryPriceX64"])
        base_mint=None
        for k in ("assetMint","baseMint","mint","tokenMint"):
            if k in d and d[k]:
                base_mint=str(d[k]); break
        return side,size_ui,entry,base_mint

    print("Decoding positions…")
    # pull raw via getMultipleAccounts (not a scan)
    for i in range(0, len(pubs), 100):
        batch = pubs[i:i+100]
        try:
            multi = rpc("getMultipleAccounts", [batch, {"encoding":"base64","commitment":"confirmed"}]) or {}
        except Exception as e:
            print("  getMultipleAccounts batch failed:", e); continue
        vals = None
        if isinstance(multi, dict):
            vals = multi.get("value")
            if vals is None and "result" in multi:
                vals = (multi["result"] or {}).get("value")
        if not isinstance(vals, list):
            for pk in batch: print(f"  {pk}: getMultipleAccounts invalid shape");
            continue
        for pk, v in zip(batch, vals):
            raw = raw_from_multi(v)
            if not isinstance(raw,(bytes,bytearray)) or len(raw)<=8:
                print(f"  {pk}: no raw bytes"); continue
            try:
                decoded = coder.decode(account_name, raw)
                d = decoded.__dict__ if hasattr(decoded,"__dict__") else decoded
                side,size_ui,entry,base_mint = extract_fields(d)
                # mark price
                mark=None
                try:
                    r = requests.get("https://price.jup.ag/v6/price", params={"ids":base_mint,"vsToken":"USDC"}, timeout=8)
                    r.raise_for_status()
                    dd = r.json().get("data",{})
                    if base_mint in dd and "price" in dd[base_mint]: mark=float(dd[base_mint]["price"])
                    elif dd: mark=float(next(iter(dd.values())).get("price"))
                except Exception: mark=None
                pnl=None
                if None not in (side,size_ui,entry,mark):
                    pnl=(mark-entry)*size_ui*(1.0 if side=="LONG" else -1.0)
                pnl_str = f"{pnl:+.4f}" if pnl is not None else "—"
                print(f"  {pk[:6]}…{pk[-6:]} | {side or '—':>5} | size={size_ui or '—'} | entry={entry or '—'} | mark={mark or '—'} | PnL={pnl_str}")
            except Exception as e:
                print(f"  {pk}: decode failed: {type(e).__name__}: {e}")


def main():
    print("== Jupiter Perps (Standalone) ==")
    print(f"RPC:     {RPC_URL}  (Helius: yes)")
    print(f"Program: {PROGRAM_ID}")
    print(f"Owner:   {OWNER_PUBKEY}\n")

    # sanity: program has accounts? (V2 object)
    res0 = rpc("getProgramAccountsV2", [PROGRAM_ID, {"encoding":"base64","limit":1}]) or {}
    accs0 = res0.get("accounts") if isinstance(res0, dict) else None
    if not (isinstance(accs0, list) and accs0):
        print("This program id returned 0 accounts (V2). Double-check PROGRAM_ID.")
        print("Done."); return

    # list my positions via V2 filters (we already know disc and offset)
    pubs = list_positions_v2(PROGRAM_ID, POSITION_DISC, OWNER_PUBKEY, OWNER_OFFSET, LIMIT_POS)
    print(f"Found {len(pubs)} position pubkeys:")
    for pk in pubs: print("  ", pk)

    # optional decode
    if IDL_PATH and pubs:
        try_decode_positions(IDL_PATH, POSITION_DISC, pubs)

    # markets disc inventory (first page)
    if SHOW_MARKETS:
        print("\nMarkets (disc inventory first page):")
        try:
            params={"encoding":"base64","dataSlice":{"offset":0,"length":8},"limit":2000}
            res=rpc("getProgramAccountsV2",[PROGRAM_ID, params]) or {}
            accs=res.get("accounts") if isinstance(res,dict) else []
            seen=Counter()
            if isinstance(accs,list):
                for it in accs:
                    data=(it.get("account") or {}).get("data") if isinstance(it, dict) else None
                    raw = raw_from_data(data)
                    if isinstance(raw,(bytes,bytearray)) and len(raw)>=8:
                        seen.update([raw[:8].hex()])
            if seen:
                print(f"  unique discs: {len(seen)}; first 10:")
                for h,c in seen.most_common(10): print("   ", h, c)
            else:
                print("  no discs found on first page.")
        except Exception as e:
            print("  disc scan failed:", e)

    print("\nDone.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
