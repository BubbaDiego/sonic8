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
    Robust extraction of base64-decoded bytes from GPA result.
    Supports:
      - ["<b64>", "base64"]
      - {"encoded":"<b64>", "encoding":"base64"}
    """
    acc = it.get("account") or {}
    data = acc.get("data")
    try:
        if isinstance(data, list) and data and isinstance(data[0], str):
            return base64.b64decode(data[0])
        if isinstance(data, dict) and "encoded" in data and isinstance(data["encoded"], str):
            return base64.b64decode(data["encoded"])
    except Exception:
        return None
    return None


async def _inner_fetch_v2(owner: str, limit: int) -> Dict[str, Any]:
    """
    Detailed decode of owner's positions, v2:
    - server-side filter (discriminator + owner@offset)
    - raw bytes extraction
    - coder.decode(account_name, raw_bytes)
    - compute side/size/entry/mark/PnL
    NEVER throws: per-row issues are recorded inline.
    """
    result: Dict[str, Any] = {"ok": True, "version": "v2", "owner": owner, "count": 0, "items": []}

    off = _owner_off()
    if off is None:
        result.update({"ok": False, "error": "PERPS_POSITION_OWNER_OFFSET not set. Probe it then set env."})
        return result

    try:
        program, client = await get_perps_program()
    except Exception as e:
        result.update({"ok": False, "error": f"IDL/program init failed: {e}"})
        return result

    try:
        pos_name = get_account_name("position", "Position")
        disc_b58 = _b58enc(get_disc("position", pos_name))
        pid = get_program_id()

        params = {
            "encoding": "base64",
            "commitment": "confirmed",
            "filters": [
                {"memcmp": {"offset": 0, "bytes": disc_b58}},
                {"memcmp": {"offset": int(off), "bytes": owner}}
            ],
            "limit": int(limit)
        }

        # Owner-filtered GPA
        try:
            res = _rpc("getProgramAccounts", [pid, params]) or []
        except Exception as e:
            result.update({"ok": False, "error": f"GPA failed: {e}"})
            return result

        coder = program.coder.accounts
        items: List[Dict[str, Any]] = []

        for it in res:
            pk = it.get("pubkey")
            raw = _raw_bytes_from_gpa_item(it)

            if not pk:
                items.append({"pubkey": "<?>", "error": "missing pubkey"})
                continue
            if not isinstance(raw, (bytes, bytearray)):
                items.append({
                    "pubkey": pk, "error": f"no-raw-bytes (type={type(raw).__name__ if raw is not None else 'None'}; "
                                            f"dataType={type((it.get('account') or {}).get('data')).__name__})"
                })
                continue
            if len(raw) <= 8:
                items.append({"pubkey": pk, "error": f"raw too short: {len(raw)}"})
                continue

            # Decode fields
            try:
                decoded = coder.decode(pos_name, raw)  # raw must be bytes
                # anchorpy objects usually expose __dict__
                d = decoded.__dict__ if hasattr(decoded, "__dict__") else decoded
                fields = extract_fields(d)             # side/size/entry/mint
                mark = get_mark_price_usdc(fields["baseMint"])
                pnl  = est_pnl_usd(fields["side"], fields["sizeUi"], fields["entryPx"], mark)
                items.append({
                    "pubkey": pk,
                    "side": fields["side"],
                    "size": fields["sizeUi"],
                    "entry": fields["entryPx"],
                    "mark": mark,
                    "pnlUsd": pnl
                })
            except Exception as e:
                items.append({
                    "pubkey": pk,
                    "error": f"decode failed: {type(e).__name__}: {e}",
                    "rawHeadHex": raw[:16].hex()
                })

        result["items"] = items
        result["count"] = len(items)
        return result

    finally:
        try:
            await client.close()
        except Exception:
            pass


def fetch_positions_detailed_v2(owner: str, limit: int = 100) -> Dict[str, Any]:
    """
    Sync wrapper for route. Returns a dict; NEVER raises.
    """
    return anyio.run(_inner_fetch_v2, owner, limit)

