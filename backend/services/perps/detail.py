from __future__ import annotations

import base64
import os
from typing import Any, Dict, List, Optional

import anyio
from solders.pubkey import Pubkey

from backend.services.perps.client import get_perps_program
from backend.services.perps.config import get_disc, get_account_name
from backend.services.perps.raw_rpc import _rpc, get_program_id
from backend.services.perps.compute import extract_fields, get_mark_price_usdc, est_pnl_usd


# ---- tiny base58 encoder (no extra deps) ----
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58enc(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    if n == 0:
        res = _B58[0]
    else:
        out = []
        while n:
            n, r = divmod(n, 58)
            out.append(_B58[r])
        res = "".join(reversed(out))
    # preserve leading zero bytes
    z = 0
    for ch in b:
        if ch == 0:
            z += 1
        else:
            break
    return (_B58[0] * z) + res


def _owner_off() -> Optional[int]:
    v = (os.getenv("PERPS_POSITION_OWNER_OFFSET") or "").strip()
    try:
        return int(v)
    except Exception:
        return None


def _raw_bytes_from_gpa_item(it: dict) -> Optional[bytes]:
    """
    Helius and some RPCs return either:
      - ["<b64>", "base64"]
      - {"encoded":"<b64>", "encoding":"base64"}
    Return bytes decoded from the base64 string or None.
    """
    data = it.get("account", {}).get("data")
    try:
        if isinstance(data, list) and data:
            return base64.b64decode(data[0])
        if isinstance(data, dict) and "encoded" in data:
            return base64.b64decode(data["encoded"])
    except Exception:
        return None
    return None


async def _inner_fetch(owner: str, limit: int) -> Dict[str, Any]:
    """
    Detailed decode of *owner's* positions:
      - filter at RPC (discriminator + owner@offset)
      - decode bytes via program.coder.accounts.decode(account_name, raw_bytes)
      - compute Side / Size / Entry / Mark / est PnL
    """
    off = _owner_off()
    if off is None:
        return {"ok": False, "error": "PERPS_POSITION_OWNER_OFFSET not set. Probe it then set env."}

    program, client = await get_perps_program()  # we only need coder from this Program
    try:
        pos_name = get_account_name("position", "Position")
        disc_b58 = _b58enc(get_disc("position", pos_name))
        pid = get_program_id()

        # pull only my positions (server-side filter)
        params = {
            "encoding": "base64",
            "commitment": "confirmed",
            "filters": [
                {"memcmp": {"offset": 0, "bytes": disc_b58}},
                {"memcmp": {"offset": int(off), "bytes": owner}}
            ],
            "limit": int(limit)
        }
        res = _rpc("getProgramAccounts", [pid, params]) or []
        items: List[Dict[str, Any]] = []

        # decode each account with coder.accounts.decode(account_name, raw_bytes)
        coder = program.coder.accounts
        for it in res:
            pk = it.get("pubkey")
            raw = _raw_bytes_from_gpa_item(it)
            if not (pk and raw and len(raw) > 8):
                continue
            try:
                decoded = coder.decode(pos_name, raw)  # <-- IMPORTANT: raw is bytes
                d = decoded.__dict__ if hasattr(decoded, "__dict__") else decoded
                f = extract_fields(d)                 # side/size/entry/mint
                mark = get_mark_price_usdc(f["baseMint"])
                pnl = est_pnl_usd(f["side"], f["sizeUi"], f["entryPx"], mark)
                items.append({
                    "pubkey": pk,
                    "side": f["side"],
                    "size": f["sizeUi"],
                    "entry": f["entryPx"],
                    "mark": mark,
                    "pnlUsd": pnl
                })
            except Exception as e:
                items.append({"pubkey": pk, "error": f"decode failed: {e}"})

        return {"ok": True, "owner": owner, "count": len(items), "items": items}
    finally:
        try:
            await client.close()
        except Exception:
            pass


def fetch_positions_detailed(owner: str, limit: int = 100) -> Dict[str, Any]:
    """
    Sync wrapper for route: run the async inner fetch in a worker-friendly loop.
    """
    return anyio.run(_inner_fetch, owner, limit)

