# backend/services/perps/detail.py
from __future__ import annotations

import base64
import os
from typing import Any, Dict, List, Optional

import anyio

from backend.services.perps.client import get_perps_program
from backend.services.perps.config import get_disc, get_account_name
from backend.services.perps.raw_rpc import _rpc, get_program_id
from backend.services.perps.compute import extract_fields, get_mark_price_usdc, est_pnl_usd


# ---------------- base58 (tiny encoder) ----------------
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def _b58enc(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    if n == 0:
        s = _B58[0]
    else:
        out = []
        while n:
            n, r = divmod(n, 58)
            out.append(_B58[r])
        s = "".join(reversed(out))
    # preserve leading zeros
    z = 0
    for ch in b:
        if ch == 0: z += 1
        else: break
    return (_B58[0] * z) + s


def _owner_off() -> Optional[int]:
    v = (os.getenv("PERPS_POSITION_OWNER_OFFSET") or "").strip()
    try:
        return int(v)
    except Exception:
        return None


# ---------------- helpers to read raw bytes ----------------
def _raw_from_gpa_item(it: dict) -> Optional[bytes]:
    """
    GPA account shapes we may see:
      - ["<b64>", "base64"]
      - {"encoded":"<b64>", "encoding":"base64"}
    """
    acc = it.get("account") or {}
    data = acc.get("data")
    try:
        if isinstance(data, list) and data and isinstance(data[0], str):
            return base64.b64decode(data[0])
        if isinstance(data, dict) and isinstance(data.get("encoded"), str):
            return base64.b64decode(data["encoded"])
    except Exception:
        return None
    return None


def _raw_from_multi_item(v: dict) -> Optional[bytes]:
    """
    getMultipleAccounts item:
      - { "data": ["<b64>", "base64"], ... }
      - { "data": {"encoded":"<b64>", "encoding":"base64"}, ... }
    """
    data = v.get("data")
    try:
        if isinstance(data, list) and data and isinstance(data[0], str):
            return base64.b64decode(data[0])
        if isinstance(data, dict) and isinstance(data.get("encoded"), str):
            return base64.b64decode(data["encoded"])
    except Exception:
        return None
    return None


def _chunks(xs: List[str], n: int) -> List[List[str]]:
    return [xs[i:i+n] for i in range(0, len(xs), n)]


# ---------------- async worker ----------------
async def _inner_fetch_v2(owner: str, limit: int) -> Dict[str, Any]:
    """
    v2 detailed decode:
      1) memcmp(discriminator) + memcmp(owner@offset) to fetch *your* pubkeys
      2) getMultipleAccounts for those pubkeys (encoding=base64)
      3) raw bytes -> coder.decode(account_name, raw)
      4) compute side/size/entry/mark/PnL (price-delta only)
    NEVER raises; problems are returned inline.
    """
    out: Dict[str, Any] = {"ok": True, "version": "v2", "owner": owner, "count": 0, "items": []}

    off = _owner_off()
    if off is None:
        out.update({"ok": False, "error": "PERPS_POSITION_OWNER_OFFSET not set. Probe then set env."})
        return out

    try:
        program, client = await get_perps_program()
    except Exception as e:
        out.update({"ok": False, "error": f"IDL/program init failed: {e}"})
        return out

    try:
        pos_name = get_account_name("position", "Position")
        disc_b58 = _b58enc(get_disc("position", pos_name))
        pid = get_program_id()

        # 1) get my position pubkeys
        params = {
            "encoding": "base64",
            "commitment": "confirmed",
            "filters": [
                {"memcmp": {"offset": 0, "bytes": disc_b58}},
                {"memcmp": {"offset": int(off), "bytes": owner}}
            ],
            "limit": int(limit)
        }
        try:
            gpa = _rpc("getProgramAccounts", [pid, params]) or []
        except Exception as e:
            out.update({"ok": False, "error": f"GPA failed: {e}"})
            return out

        pubkeys = [it.get("pubkey") for it in gpa if isinstance(it.get("pubkey"), str)]
        if not pubkeys:
            out.update({"note": "no positions for owner (disc+owner filter returned 0)"})
            return out

        # 2) fetch those pubkeys with getMultipleAccounts (safe chunks)
        coder = program.coder.accounts
        rows: List[Dict[str, Any]] = []

        for batch in _chunks(pubkeys, 100):
            try:
                multi = _rpc("getMultipleAccounts", [batch, {"encoding":"base64","commitment":"confirmed"}]) or {}
                vals = None
                if isinstance(multi, dict):
                    vals = multi.get("value")
                    if vals is None and "result" in multi:
                        vals = (multi["result"] or {}).get("value")
                if not isinstance(vals, list):
                    # invalid shape; fall back to GPA raw per-pubkey
                    for pk in batch:
                        it = next((x for x in gpa if x.get("pubkey")==pk), None)
                        raw = _raw_from_gpa_item(it) if it else None
                        if isinstance(raw, (bytes, bytearray)) and len(raw) > 8:
                            _decode_one(rows, coder, pos_name, pk, raw)
                        else:
                            rows.append({"pubkey": pk, "error": "getMultipleAccounts invalid shape"})
                    continue

                for pk, v in zip(batch, vals):
                    raw = _raw_from_multi_item(v) if isinstance(v, dict) else None
                    if not isinstance(raw, (bytes, bytearray)) or len(raw) <= 8:
                        # try GPA fallback
                        it = next((x for x in gpa if x.get("pubkey")==pk), None)
                        raw = _raw_from_gpa_item(it) if it else None
                    if not isinstance(raw, (bytes, bytearray)) or len(raw) <= 8:
                        rows.append({"pubkey": pk, "error": "no-raw-bytes from multi/gpa"})
                        continue
                    _decode_one(rows, coder, pos_name, pk, raw)

            except Exception as e:
                rows.append({"pubkey": "<?>", "error": f"getMultipleAccounts batch failed: {e}"})

        out["items"] = rows
        out["count"] = len(rows)
        return out

    finally:
        try:
            await client.close()
        except Exception:
            pass


def _decode_one(rows: List[Dict[str, Any]], coder, account_name: str, pk: str, raw: bytes) -> None:
    try:
        decoded = coder.decode(account_name, raw)
        d = decoded.__dict__ if hasattr(decoded, "__dict__") else decoded
        f = extract_fields(d)               # side/size/entry/mint
        mark = get_mark_price_usdc(f["baseMint"])
        pnl  = est_pnl_usd(f["side"], f["sizeUi"], f["entryPx"], mark)
        rows.append({
            "pubkey": pk,
            "side": f["side"],
            "size": f["sizeUi"],
            "entry": f["entryPx"],
            "mark":  mark,
            "pnlUsd": pnl
        })
    except Exception as e:
        rows.append({"pubkey": pk, "error": f"decode failed: {type(e).__name__}: {e}", "rawHeadHex": raw[:16].hex()})


# ---------------- sync wrapper that routes call ----------------
def fetch_positions_detailed_v2(owner: str, limit: int = 100) -> Dict[str, Any]:
    """Return dict; NEVER raises."""
    return anyio.run(_inner_fetch_v2, owner, limit)
