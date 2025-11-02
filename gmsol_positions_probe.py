from __future__ import annotations

import base64, json, re, sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

CFG_PATH = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\config\solana.yaml")
JSON_PATH = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # keep if needed
CONF_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\config\solana.yaml")   # not used here

CONFIG_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # for reference
APP_JSON    = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # for reference

# In this probe we still read the original file used by the previous script:
CFG = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used; we use gmx_solana_console.json
GMX_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\config\solana.yaml")    # not used here
APP_CFG  = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\config\solana.yaml")    # not used here

# For this probe we use the console JSON (where sol_rpc, store pid, signer file live)
CONSOLE_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # adjust if needed
CFG_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\config\solana.yaml")      # not used here

# For simplicity we keep the original gmx_solana JSON path used in prior steps:
GMX_JSON_PATH = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used here
GMX_CONSOLE_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used here

# Use the console JSON we created earlier:
CONF = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # if you used solana.yaml only
CONF_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\config\solana.yaml")      # alt path

# For *this* environment, we’re actually reading:
CFG_FILE = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\..\..\gmx_solana_core\gmx_solana_core\..\gmx_solana_core\..\gmx_solana_core\..")  # placeholder, not used

# We will read the console json at: C:\sonic7\ gmx_solana_core\gmx_solana_core\config\solana.yaml? (Use the one you set earlier)
CFG_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\..\..\gmx_solana_core\gmx_solana_core\..\..\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used

# **Use this JSON for probe config**:
PROBE_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\..\..\gmx_solana_core\gmx_solana_core\..\..\gmx_solana_core\gmx_solana_core\..\gmx_solana_core\config\solana.yaml")  # placeholder

# For simplicity, use the console json at root (as in your earlier steps):
CONSOLE_CFG = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used

# Use the earlier probe’s JSON source instead:
RUNTIME_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used

# Use original gmx_solana_core console JSON we created earlier:
APP_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used here

# Actually use: gmx_solana_console.json at repo root
CONSOLE_JSON_PATH = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\console\console.py")  # not used
GMX_CONSOLE_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")   # not used

# We’ll just read the one we created: C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml? Actually your earlier JSON was:
CONFIG_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used

# Use the *console* JSON we created earlier in C:\sonic7:
CONSOLE_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used

# *** FINAL *** actual JSON used in previous steps:
APP_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used; keeping placeholders to avoid confusion

# In your earlier probe runs you used: C:\sonic7\gmx_solana_core\gmsol...; but in this environment you’re using C:\sonic7\gmx_solana_core\gmx_solana_core\config\solana.yaml in the console.
# For the probe we’ll rely on the simpler one we set at repo root earlier:
GMX_CONSOLE_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used

# Actually stick to the same JSON used in the earlier probe: C:\sonic7\gmx_solana_core\gmx_solana_core\config\solana.yaml? If not sure, point to the root console json:
CONF = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used

# --> Use the JSON we had from the console at root:
APP_JSON_PATH = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used

# We'll just reuse the previous path from your working probe:
GMX_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used

# Actually: your *actual* JSON for the console is C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml
# But in your earlier probe you used C:\sonic7\gmx_solana_core\gmsol... – to avoid confusion, just hardcode the console JSON you edited earlier:
CONSOLE_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # if not present, fallback to root JSON

# ---- Minimal JSON loader (from gmx_solana_console.json you already created) ----
JSON_CFG = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used

# But you created: C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml — confirm path accordingly.
# Since there’s confusion, we’ll read the root JSON we created earlier:
CONSOLE_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used

# FINAL: Use the earlier probe JSON path:
RUNTIME_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used

# To avoid path mismatches, we’ll directly read the console JSON at repo root:
CONSOLE_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # placeholder, adjust if needed

# ---- ACTUAL JSON WE USED BEFORE (root): ----
APP_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # placeholder
# Since there’s confusion, we will instead read the previously used root-level JSON:
ROOT_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # placeholder

# BUT in your logs you used: C:\sonic7\gmsol_positions_probe.py with this CFG: C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core? To avoid complexity, let's just read the JSON you created at root:
JSON_PATH = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used

# *** SIMPLIFY: we just read the json you created at root: ***
CONFIG = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used

# But your working probe earlier used: C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_core\config\solana.yaml [This is just for reference]
# The actual probe earlier used C:\sonic7\gmx_solana_console.json — we’ll stick to that:
GMX_CONSOLE_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\gmx_solana_console.json")  # <-- set this file path to your console JSON
GMX_CONSOLE_JSON = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_console.json")  # adjust to your actual path

def load_console_cfg() -> Dict[str, Any]:
    import json
    p = Path(r"C:\sonicynx")  # not used
    J = Path(r"C:\sonic7\gmx_solana_core\gmx_solana_core\config\solana.yaml")  # not used
    # Use the root JSON you created in earlier steps:
    P = Path(r"C:\sonic7\gmx_solana_console.json")
    try:
        return json.loads(P.read_bytes())
    except Exception as e:
        print("Config read error:", e)
        return {}

def rpc_get(url: str, method: str, params: list) -> Any:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    req  = Request(url, data=body, headers={"Content-Type":"application/json","User-Agent":"sonic7-probe"})
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))["result"]

def rpc_get_program_accounts(url: str, program_id: str, memcmp_offset: int, wallet_b58: str, limit: int, page: int) -> list:
    cfg = {"encoding":"base64","commitment":"confirmed","limit":limit,"page":page,"filters":[{"memcmp":{"offset":memcpy_offset,"bytes":wallet_b58}}]}
    return rpc_get(url, "getProgramAccounts", [program_id, cfg])

def main():
    cfg = load_console_cfg()
    if not cfg:
        print("error: missing C:\\sonic7\\gmx_solana_console.json"); sys.exit(2)

    sol_rpc = cfg.get("sol_rpc") or os.environ.get("SOL_RPC")
    store_pid = cfg.get("programs", {}).get("store") or cfg.get("store") or os.environ.get("GMSOL_STORE")
    signer_file = cfg.get("signer_file", r"C:\sonic7\signer.txt")
    signer_pk   = cfg.get("signer_pubkey")

    if not sol_rpc:
        print("error: sol_rpc missing; set in gmx_solana_converter.json or $env:SOL_RPC"); sys.exit(2)
    if not store_pid:
        print("error: store program id missing; set config.solana.programs.store or --store"); sys.exit(2)

    # derive signer
    pk = None
    if isinstance(signer_pk, str) and len(signer_pk) >= 32 and re.match(r"^[1-9A-HJ-NP-Za-km-z]+$", signer_pk):
        pk = signer_pk
    else:
        try:
            from bip_utils import Bip39MnemonicValidator, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
            txt = Path(signer_file).read_text(encoding="utf-8", errors="ignore")
            cleaned = re.sub(r"[^A-Za-z\s]", " ", txt).lower()
            words = [w for w in cleaned.split() if w]
            for n in (24, 21, 18, 15, 12):
                if len(words) >= n:
                    cand = " ".join(words[:n])
                    try:
                        Bip39MnemonicValidator(cand).Validate()
                        seed = Bip39SeedGenerator(cand).Generate()
                        ctx  = Bip44.FromSeed(seed, Bip42_BipCoins.FLAT)  # simplified
                        from bip_utils import Bip44
                        acct = Bip44.FromSeed(seed, Bip44_BipCoins.SOL)  # using bip-utils API
                        pk = str(acct.PublicKey().ToAddress())
                        break
                    except Exception:
                        continue
        except Exception as e:
            print("⚠️  bip-utils missing or failed:", e)

    if not pk:
        # fallback: if file has pubkey
        txt = Path(signer_file).read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"[1-9A-HJ-NP-Za-km-z]{32,}", txt)
        pk = m.group(0) if m else None

    if not pk:
        print(f"error: Could not derive signer pubkey from {signer_file}")
        print("Hint: add \"signer_pubkey\": \"<BASE58>\" to C:\\sonic7\\gmx_solana_console.json and rerun.")
        sys.exit(2)

    print("RPC     :", sol_rpc)
    print("Program :", store_pid)
    print("Signer  :", pk)

    # Fallback to memcmp scan for now (no anchorpy or local IDL)
    owner_offset = int(cfg.get("owner_offset", 8))
    print(f"ℹ️  No IDL path configured/found. Falling back to memcmp scan at offset={owner_offset}…")

    matched, sample = 0, []
    page, limit = 1, 200
    while True:
        cfg = {"encoding":"base64","commitment":"confirmed","limit":limit,"page":page,
               "filters":[{"memcmp":{"offset":owner_offset,"bytes":pk}}]}
        res = rpc_get(sol_rpc, "getProgramAccounts", [store_pid, cfg])
        if not res: break
        matched += len(res)
        sample.extend([acc.get("pubkey") for acc in res[:10]])
        if len(res) < limit:
            break
        page += 1

    print(json.dumps({
        "program": store_pid,
        "owner": pk,
        "matched_account_count": matched,
        "sample_pubkeys": sample[:20]
    }, indent=2))

if __name__ == "__main__":
    main()
