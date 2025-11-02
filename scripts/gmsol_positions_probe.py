from __future__ import annotations
import asyncio, base64, json, sys, re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

CFG_PATH = Path(r"C:\sonic7\gmx_solana_console.json")
LOCAL_IDL = Path(r"C:\sonic7\backend\core\gmsol\idl\gmsol-store.json")  # put a local idl here if on-chain isn't available

def die(msg: str, code: int = 2):
    print(f"error: {msg}")
    sys.exit(code)

def load_cfg() -> Dict[str, Any]:
    try:
        return json.loads(CFG_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        die(f"Config not found or unreadable: {e}")

def rpc_call(rpc_url: str, method: str, params: Optional[List[Any]] = None, timeout: float = 20.0) -> Any:
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params or []}).encode("utf-8")
    req = Request(rpc_url, data=body, headers={"Content-Type":"application/json","User-Agent":"sonic7-gmsol-probe"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as e:
        die(f"RPC {method} failed: {e}")
    if "error" in data:
        die(f"RPC {method} error: {data['error']}")
    return data["result"]

def gpa_v2(rpc_url: str, program_id: str, limit: int, page: int) -> List[Dict[str,Any]]:
    res = rpc_call(rpc_url, "getProgramAccountsV2", [program_id, {
        "encoding":"base64", "commitment":"confirmed", "limit":limit, "page":page
    }])
    if isinstance(res, list): return res
    if isinstance(res, dict):
        for k in ("value","accounts","items"):
            v = res.get(k)
            if isinstance(v, list): return v
    return []

def derive_signer_pub(path: str) -> Optional[str]:
    """
    Same tolerant logic as the menu:
      1) if a base58 pubkey appears anywhere in the file, use it
      2) else derive from a BIP-39 mnemonic (strip punctuation, lowercase, 12/15/18/21/24 words)
    """
    from pathlib import Path
    import re
    p = Path(path)
    if not p.exists():
        return None

    txt = p.read_text(encoding="utf-8", errors="ignore")

    # 1) Prefer base58 token if present
    m = re.search(r"[1-9A-HJ-NP-Za-km-z]{32,}", txt)
    if m:
        return m.group(0)

    # 2) Tolerant mnemonic → Solana pubkey m/44'/501'/0'/0'
    try:
        from bip_utils import Bip39MnemonicValidator, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
        cleaned = re.sub(r"[^A-Za-z\s]", " ", txt).lower()
        words = [w for w in cleaned.split() if w]
        for n in (24, 21, 18, 15, 12):
            if len(words) >= n:
                cand = " ".join(words[:n])
                try:
                    Bip39MnemonicValidator(cand).Validate()
                    seed = Bip39SeedGenerator(cand).Generate()
                    ctx  = Bip44.FromSeed(seed, Bip44Coins.SOLANA)
                    acct = ctx.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(0)
                    return acct.PublicKey().ToAddress()
                except Exception:
                    continue
    except Exception:
        # bip-utils not present in THIS interpreter (install in venv): pip install bip-utils
        pass

    return None

# Keep backwards-compat so old code paths work
derive_pub_from_signer = derive_signer_pub


# Backward-compat alias
derive_pub_from_signer = derive_signer_pub


async def fetch_onchain_idl(program_id: str, rpc_url: str) -> Optional[Dict[str,Any]]:
    try:
        from anchorpy import Idl
        from solana.publickey import PublicKey
        from solana.rpc.async_api import AsyncClient
    except Exception as e:
        print("ℹ️  anchorpy import failed:", e); return None
    client = AsyncClient(rpc_url)
    try:
        idl = await Idl.fetch(client, PublicKey(program_id))
        return idl.__dict__
    except Exception:
        return None
    finally:
        await client.close()

def load_local_idl() -> Optional[Dict[str,Any]]:
    if LOCAL_IDL.exists():
        try: return json.loads(LOCAL_IDL.read_text(encoding="utf-8"))
        except Exception: return None
    return None

def account_names(idl_dict: Dict[str,Any]) -> List[str]:
    out = []
    for a in (idl_dict.get("accounts") or []):
        if isinstance(a.get("name"), str): out.append(a["name"])
    return out

def build_coder(idl_dict: Dict[str,Any]):
    from anchorpy import Idl, Coder
    idl = Idl.from_json(idl_dict)
    return Coder(idl)

def decode_one(coder, names: List[str], raw_b64: str) -> Optional[Dict[str,Any]]:
    import base64
    data = base64.b64decode(raw_b64)
    for nm in names:
        try:
            obj = coder.accounts.decode(nm, data)
            return {"__account__": nm, **(obj.__dict__ if hasattr(obj,"__dict__") else obj)}
        except Exception:
            continue
    return None

def main():
    cfg = load_cfg()
    rpc_url = cfg.get("sol_rpc") or ""
    pid     = cfg.get("store_program_id") or ""
    signer  = derive_pub_from_signer(cfg.get("signer_file",""))
    if not rpc_url: die("sol_rpc missing in JSON.")
    if not pid:     die("store_program_id missing. Use the GMX Store PID.")
    if not signer:  die(f"Could not derive signer pubkey from {cfg.get('signer_file')}")

    print("RPC     :", rpc_url)
    print("Program :", pid)
    print("Signer  :", signer)

    # load IDL
    idl = asyncio.run(fetch_onchain_idl(pid, rpc_url))
    if not idl:
        idl = load_local_idl()
    if not idl:
        die(f"IDL not available. Fetch once:\n  anchor idl fetch -o {LOCAL_IDL} {pid}")

    names = account_names(idl)
    if not names: die("IDL has no accounts definitions to decode.")

    coder = build_coder(idl)

    checked = 0
    matches: List[Dict[str,Any]] = []
    limit, page, max_pages = 200, 1, 25

    while page <= max_pages:
        accs = gpa_v2(rpc_url, pid, limit, page)
        if not accs: break
        for a in accs:
            ad = a.get("account", {}).get("data")
            raw_b64 = ad[0] if isinstance(ad, list) and ad else (ad if isinstance(ad, str) else None)
            if not raw_b64: continue
            decoded = decode_one(coder, names, raw_b64)
            if not decoded: continue
            # heuristic owner field names
            owner = None
            for k in ("owner","authority","trader","user","wallet"):
                v = decoded.get(k)
                if isinstance(v, str) and len(v) >= 32: owner = v; break
            if owner == signer:
                matches.append({"pubkey": a.get("pubkey"), "account_type": decoded.get("__account__"), "data": decoded})
        checked += len(accs)
        if len(accs) < limit: break
        page += 1

    print(json.dumps({
        "program": pid, "owner": signer, "checked_accounts": checked,
        "matches": len(matches), "positions": matches[:50]
    }, indent=2))

if __name__ == "__main__":
    main()
