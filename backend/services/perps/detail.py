from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from solders.pubkey import Pubkey
import anyio

from backend.services.perps.client import get_perps_program
from backend.services.perps.config import get_disc, get_account_name
from backend.services.perps.raw_rpc import _rpc, get_program_id
from backend.services.perps.compute import extract_fields, get_mark_price_usdc, est_pnl_usd

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def _b58enc(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    if n == 0: res = _B58[0]
    else:
        out=[]
        while n: n,r=divmod(n,58); out.append(_B58[r])
        res="".join(reversed(out))
    z=0
    for ch in b:
        if ch==0: z+=1
        else: break
    return (_B58[0]*z)+res

def _owner_off() -> Optional[int]:
    v = (os.getenv("PERPS_POSITION_OWNER_OFFSET") or "").strip()
    try: return int(v)
    except Exception: return None

async def _inner_fetch(owner: str, limit: int) -> Dict[str, Any]:
    off = _owner_off()
    if off is None:
        return {"ok": False, "error": "PERPS_POSITION_OWNER_OFFSET not set."}
    program, client = await get_perps_program()
    try:
        pos_name = get_account_name("position", "Position")
        disc_b58 = _b58enc(get_disc("position", pos_name))
        params = {
            "encoding": "base64",
            "commitment": "confirmed",
            "filters": [
                {"memcmp": {"offset": 0, "bytes": disc_b58}},
                {"memcmp": {"offset": int(off), "bytes": owner}}
            ],
            "limit": int(limit)
        }
        pid = get_program_id()
        res = _rpc("getProgramAccounts", [pid, params])
        pubs = [r.get("pubkey") for r in (res or []) if r.get("pubkey")]

        out: List[Dict[str, Any]] = []
        acc = program.account[pos_name]
        for pk in pubs:
            try:
                obj = await acc.fetch(Pubkey.from_string(pk))
                d = obj.__dict__ if hasattr(obj, "__dict__") else obj
                f = extract_fields(d)
                mark = get_mark_price_usdc(f["baseMint"])
                pnl = est_pnl_usd(f["side"], f["sizeUi"], f["entryPx"], mark)
                out.append({
                    "pubkey": pk,
                    "side": f["side"],
                    "size": f["sizeUi"],
                    "entry": f["entryPx"],
                    "mark": mark,
                    "pnlUsd": pnl
                })
            except Exception as e:
                out.append({"pubkey": pk, "error": f"decode failed: {e}"})
        return {"ok": True, "owner": owner, "count": len(out), "items": out}
    finally:
        await client.close()

def fetch_positions_detailed(owner: str, limit: int = 100) -> Dict[str, Any]:
    """Sync wrapper so routes can call in a worker thread."""
    return anyio.run(_inner_fetch, owner, limit)
