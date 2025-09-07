from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json, urllib.request

router = APIRouter(prefix="/api/solana", tags=["solana"])

DEFAULT_RPC = "https://api.mainnet-beta.solana.com"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
LAMPORTS_PER_SOL = 1_000_000_000


class BalanceBody(BaseModel):
    address: str
    rpc_url: str | None = None
    include_tokens: bool = True
    commitment: str = "finalized"  # finalized|confirmed|processed


def _rpc_call(rpc: str, method: str, params: list):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(rpc, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        resp = json.loads(r.read().decode("utf-8"))
    if "error" in resp:
        raise HTTPException(status_code=400, detail=resp["error"])
    return resp["result"]


@router.post("/balance")
def solana_balance(body: BalanceBody):
    rpc = body.rpc_url or DEFAULT_RPC
    addr = body.address

    # SOL balance
    bal_res = _rpc_call(rpc, "getBalance", [addr, {"commitment": body.commitment}])
    lamports = int(bal_res["value"])
    sol = lamports / LAMPORTS_PER_SOL

    out = {
        "address": addr,
        "rpc": rpc,
        "commitment": body.commitment,
        "sol": {"lamports": lamports, "sol": sol},
        "tokens": [],
        "context": {"slot": bal_res["context"]["slot"]},
    }

    ta_lamports_sum = 0

    if body.include_tokens:
        ta_res = _rpc_call(
            rpc,
            "getTokenAccountsByOwner",
            [addr, {"programId": TOKEN_PROGRAM}, {"encoding": "jsonParsed", "commitment": body.commitment}],
        )
        out["context"]["slot"] = max(out["context"]["slot"], ta_res["context"]["slot"])
        for it in ta_res["value"]:
            acc = it["account"]
            lam = int(acc.get("lamports", 0))
            ta_lamports_sum += lam
            info = acc["data"]["parsed"]["info"]
            ta = info["tokenAmount"]
            ui_str = ta.get("uiAmountString")
            ui = float(ui_str) if ui_str is not None else float(ta.get("uiAmount", 0))
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
        "solIncludingRent": (lamports + ta_lamports_sum) / LAMPORTS_PER_SOL,
    }
    return out
