from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import time, json, urllib.request

router = APIRouter(prefix="/api/wallets", tags=["wallets-verify"])

DEFAULT_RPC = "https://api.mainnet-beta.solana.com"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
LAMPORTS_PER_SOL = 1_000_000_000

# Priority tokens for the UI (symbol map)
MINT_SYMBOL = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs": "WETH",
    "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E": "WBTC",
}
# "SOL" is native; we inject it from native balance

# ── tiny in-memory cache (address → {expires, payload}) ───────────────────────
_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = 60  # seconds

def _rpc_call(rpc: str, method: str, params: list) -> dict:
    body = json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    req  = urllib.request.Request(rpc, data=body, headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req) as r:
        resp = json.loads(r.read().decode("utf-8"))
    if "error" in resp:
        raise HTTPException(status_code=400, detail=resp["error"])
    return resp["result"]

def _normalize_top_tokens(entry: dict) -> List[dict]:
    """
    Build a 'top' list sorted by amount (desc) including native SOL and non-zero SPL tokens.
    Priority tokens float to the top (USDC/SOL/WETH/WBTC).
    """
    # native SOL as virtual token
    top = [{
        "symbol": "SOL",
        "mint": "native",
        "amount": entry["sol"]["sol"],
        "decimals": 9,
        "kind": "native",
        "tokenAccount": None,
    }]
    # add SPL non-zero
    for t in entry.get("tokens", []):
        top.append({
            "symbol": MINT_SYMBOL.get(t["mint"], None),
            "mint": t["mint"],
            "amount": t["amount"],
            "decimals": t["decimals"],
            "kind": "spl",
            "tokenAccount": t["tokenAccount"],
        })
    # priority boost: SOL, USDC, WETH, WBTC first; then others by amount desc
    prio = {"SOL", "USDC", "WETH", "WBTC"}
    def key_fn(x):
        pri = 0 if (x["symbol"] in prio if x["symbol"] else False) else 1
        return (pri, -float(x["amount"]))
    top.sort(key=key_fn)
    return top

def _fetch_one(address: str, rpc: str, commitment: str) -> dict:
    # cache check
    now = time.time()
    c = _CACHE.get(address)
    if c and c["exp"] > now:
        return c["val"]

    # SOL balance
    bal_res = _rpc_call(rpc, "getBalance", [address, {"commitment": commitment}])
    lamports = int(bal_res["value"])
    sol = lamports / LAMPORTS_PER_SOL
    out = {
        "address": address,
        "rpc": rpc,
        "commitment": commitment,
        "sol": {"lamports": lamports, "sol": sol},
        "tokens": [],
        "context": {"slot": bal_res["context"]["slot"]},
    }

    # SPL tokens (jsonParsed for uiAmount)
    ta_res = _rpc_call(
        rpc,
        "getTokenAccountsByOwner",
        [address, {"programId": TOKEN_PROGRAM}, {"encoding":"jsonParsed","commitment": commitment}],
    )
    out["context"]["slot"] = max(out["context"]["slot"], ta_res["context"]["slot"])
    ta_lamports_sum = 0
    for it in ta_res["value"]:
        acc = it["account"]
        ta_lamports_sum += int(acc.get("lamports", 0))
        info = acc["data"]["parsed"]["info"]
        ta  = info["tokenAmount"]
        ui_str = ta.get("uiAmountString")
        ui     = float(ui_str) if ui_str is not None else float(ta.get("uiAmount", 0))
        if ui > 0:
            out["tokens"].append({
                "mint": info["mint"],
                "amount": ui,
                "decimals": ta["decimals"],
                "tokenAccount": it["pubkey"],
            })
    out["tokenAccountsLamports"] = ta_lamports_sum
    out["totalLamportsControlled"] = lamports + ta_lamports_sum
    out["totals"] = {
        "solOnly": sol,
        "solIncludingRent": (lamports + ta_lamports_sum) / LAMPORTS_PER_SOL
    }
    out["top"] = _normalize_top_tokens(out)

    # cache store
    _CACHE[address] = {"exp": now + _CACHE_TTL, "val": out}
    return out

# ── Pydantic models ───────────────────────────────────────────────────────────
class VerifyBody(BaseModel):
    address: str = Field(..., description="Solana base58 address")
    rpc_url: Optional[str] = None
    commitment: str = "finalized"

class VerifyBulkBody(BaseModel):
    addresses: List[str]
    rpc_url: Optional[str] = None
    commitment: str = "finalized"

@router.post("/verify")
def verify_one(body: VerifyBody):
    rpc = body.rpc_url or DEFAULT_RPC
    return _fetch_one(body.address.strip(), rpc, body.commitment)

@router.post("/verify-bulk")
def verify_bulk(body: VerifyBulkBody):
    rpc = body.rpc_url or DEFAULT_RPC
    out = {}
    for addr in body.addresses:
        a = addr.strip()
        if not a: 
            continue
        try:
            out[a] = _fetch_one(a, rpc, body.commitment)
        except HTTPException as e:
            out[a] = {"error": True, "detail": e.detail}
        except Exception as e:
            out[a] = {"error": True, "detail": str(e)}
    return out
