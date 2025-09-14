#!/usr/bin/env python3
# Jupiter Perps — standalone (no CLI args)
# - Uses Helius getProgramAccountsV2 (object shape)
# - Derives Position discriminator from KNOWN_POSITION_PUBKEY
# - Learns true owner offset by scanning raw bytes for OWNER pubkey
# - Lists YOUR positions (disc@0 + owner@offset)
# - Optional decode (IDL_PATH + anchorpy)

from __future__ import annotations

import base64, hashlib, json, random, time, requests
from collections import Counter
from typing import Any, Dict, List, Optional


#setx PERPS_POSITION_OWNER_OFFSET 8
#setx PERPS_POSITION_DISC 0xaabc8fe47a40f7d0
#setx PERPS_PROGRAM_ID PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu


# =============== CONFIG (edit if needed) ===============
OWNER_PUBKEY   = "V8iveiirFvX7m7psPHWBJW85xPk1ZB6U4Ep9GUV2THW"
PROGRAM_ID     = "PERPHjGBqRHArX4DySjwM6UJHiR3sWAatqfdBS2qQJu"  # verified from pool owner
HELIUS_API_KEY = "a8809bee-20ba-48e9-b841-0bd2bafd60b9"
RPC_URL        = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# >>> Your known Position account (from helper)
KNOWN_POSITION_PUBKEY = "2ZwGG1dKAHCQErH3cNychmQm6tBWSLdhKQrSc2XKP6hZ"

# Optional: canonical Anchor JSON IDL to enable decode (with anchorpy)
IDL_PATH       = ""   # e.g. r"C:\sonic5\backend\services\perps\idl\jupiter_perpetuals.json"

# How many positions to fetch/print
LIMIT_POS      = 100
SHOW_MARKETS   = True
# =======================================================

# --- base58 helpers ---
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
    # preserve leading zeros as '1'
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

# --- robust Helius JSON-RPC ---
def rpc(method: str, params: Any, retries: int = 6, base_delay: float = 0.5) -> Any:
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
                raise RuntimeError(f"RPC error: {msg}")
            return data.get("result")
        except Exception as e:
            last=e; time.sleep(base_delay*(2**i)+random.uniform(0,0.25))
    raise RuntimeError(f"RPC failed: {last}")

# --- raw helpers ---
def raw_from_data(data: Any) -> Optional[bytes]:
    try:
        if isinstance(data, list) and data and isinstance(data[0], str):
            return base64.b64decode(data[0])
        if isinstance(data, dict) and isinstance(data.get("encoded"), str):
            return base64.b64decode(data["encoded"])
    except Exception:
        return None
    return None

def get_account_info(pubkey: str, encoding: str = "base64", data_slice: Optional[dict] = None) -> Optional[dict]:
    enc = {"encoding": encoding, "commitment":"confirmed"}
    if data_slice: enc["dataSlice"] = data_slice
    res = rpc("getAccountInfo", [pubkey, enc]) or {}
    v = res.get("value") if isinstance(res, dict) else None
    return v if isinstance(v, dict) else None

def get_account_space(pubkey: str) -> Optional[int]:
    # 'space' is present in jsonParsed for most accounts; fallback to a safe cap
    v = get_account_info(pubkey, encoding="jsonParsed")
    if v and isinstance(v.get("space"), int):
        return int(v["space"])
    return None  # unknown

def get_account_bytes(pubkey: str, length: int) -> Optional[bytes]:
    v = get_account_info(pubkey, data_slice={"offset":0, "length":length})
    return raw_from_data(v.get("data")) if v else None

# --- V2 helpers (object shape) ---
def program_has_any_accounts_v2(pid: str) -> bool:
    try:
        res = rpc("getProgramAccountsV2", [pid, {"encoding":"base64","limit":1}]) or {}
        accs = res.get("accounts") if isinstance(res, dict) else None
        return isinstance(accs, list) and len(accs) > 0
    except Exception:
        return False

def list_positions_v2(pid: str, disc: bytes, owner: str, owner_off: int, limit: int) -> List[str]:
    params = {"encoding":"base64","limit":limit, "filters":[
        {"memcmp":{"offset":0,"bytes": b58enc(disc)}},
        {"memcmp":{"offset":int(owner_off),"bytes": owner}}
    ]}
    res = rpc("getProgramAccountsV2", [pid, params]) or {}
    accs = res.get("accounts") if isinstance(res, dict) else []
    pubs=[]
    if isinstance(accs, list):
        for it in accs:
            if isinstance(it, dict) and isinstance(it.get("pubkey"), str):
                pubs.append(it["pubkey"])
    return pubs

# --- optional decode (console print) ---
def try_decode_positions(idl_path: str, pubs: List[str]) -> None:
    try:
        from anchorpy import Idl
        from anchorpy.coder.accounts import AccountCoder
        with open(idl_path,"r",encoding="utf-8") as f:
            idl_json = json.load(f)
        coder = AccountCoder(Idl.from_json(idl_json))
    except Exception as e:
        print(f"\nNOTE: cannot decode (anchorpy/IDL): {e}\n"); return

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
                decoded = coder.decode("Position", raw)
                d = decoded.__dict__ if hasattr(decoded,"__dict__") else decoded
                side,size_ui,entry,base_mint = extract_fields(d)
                # mark
                mark=None
                try:
                    r=requests.get("https://price.jup.ag/v6/price", params={"ids":base_mint,"vsToken":"USDC"}, timeout=8)
                    r.raise_for_status()
                    data=r.json().get("data",{})
                    if base_mint in data and "price" in data[base_mint]: mark=float(data[base_mint]["price"])
                    elif data: mark=float(next(iter(data.values())).get("price"))
                except Exception: mark=None
                pnl=None
                if None not in (side,size_ui,entry,mark): pnl=(mark-entry)*size_ui*(1.0 if side=="LONG" else -1.0)
                pnl_str=f"{pnl:+.4f}" if pnl is not None else "—"
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

    # A) derive Position discriminator from your known position account
    if not KNOWN_POSITION_PUBKEY:
        print("KNOWN_POSITION_PUBKEY is empty. Set it at the top of the script and run again.")
        print("Done."); return

    # read first 8 bytes (discriminator) from known position
    raw8 = get_account_bytes(KNOWN_POSITION_PUBKEY, 8)
    if not (isinstance(raw8,(bytes,bytearray)) and len(raw8)>=8):
        print("Could not read 8-byte head from KNOWN_POSITION_PUBKEY. Try again.")
        print("Done."); return
    pos_disc = raw8[:8]
    print(f"Derived Position discriminator (hex): {pos_disc.hex()}")

    # B) find true owner offset by scanning the KNOWN_POSITION_PUBKEY's full bytes
    space = get_account_space(KNOWN_POSITION_PUBKEY) or 4096
    full = get_account_bytes(KNOWN_POSITION_PUBKEY, min(space, 8192))
    if not isinstance(full,(bytes,bytearray)):
        print("Could not fetch full bytes for KNOWN_POSITION_PUBKEY; falling back to offset probe.")
        owner_off = None
    else:
        idx = full.find(OWNER_BYTES)
        owner_off = idx if idx >= 0 else None
        print(f"Owner bytes found at offset: {owner_off}" if owner_off is not None else "Owner bytes not found; will probe offsets.")

    # If not found in bytes, probe offsets with disc quickly (8..space step 4)
    if owner_off is None:
        for off in range(8, min(space, 2048), 4):
            params = {"encoding":"base64","limit":1, "filters":[
                {"memcmp":{"offset":0,"bytes": b58enc(pos_disc)}},
                {"memcmp":{"offset":off,"bytes": OWNER_PUBKEY}}
            ]}
            try:
                res = rpc("getProgramAccountsV2", [PROGRAM_ID, params]) or {}
                accs = res.get("accounts") if isinstance(res, dict) else []
                if isinstance(accs, list) and accs:
                    owner_off = off; break
            except Exception:
                continue
    if owner_off is None:
        owner_off = 8
    print(f"Using owner offset: {owner_off}\n")

    # C) list my positions via V2 filters (disc@0 + owner@offset)
    pubs = list_positions_v2(PROGRAM_ID, pos_disc, OWNER_PUBKEY, owner_off, LIMIT_POS)
    print(f"Found {len(pubs)} position pubkeys:")
    for pk in pubs: print("  ", pk)

    # D) optional decode
    if IDL_PATH and pubs:
        try_decode_positions(IDL_PATH, pubs)

    # E) tiny markets overview (first page discs)
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
