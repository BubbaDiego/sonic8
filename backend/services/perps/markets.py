# backend/services/perps/markets.py
from __future__ import annotations

import base64
from typing import Dict, List

from backend.services.perps.raw_rpc import _rpc, get_program_id, get_idl_account_names
from backend.services.perps.config import get_disc, get_account_name


def _filter_params(disc: bytes) -> dict:
    """getProgramAccounts params object with memcmp filter on discriminator (offset=0)."""
    return {
        "encoding": "base64",
        "filters": [
            {"memcmp": {"offset": 0, "bytes": base64.b64encode(disc).decode("utf-8")}}
        ],
        "commitment": "confirmed"
    }


def list_markets_sync() -> Dict[str, object]:
    """
    SAFE, FAST: return ONLY pubkeys of Pool and Custody accounts using
    server-side memcmp filter on the Anchor discriminator. No Anchor decode.
    """
    program_id = get_program_id()
    idl_accounts = get_idl_account_names()

    # Allow overrides via env
    pool_name_cfg = get_account_name("pool", "Pool")
    cust_name_cfg = get_account_name("custody", "Custody")
    pool_disc = get_disc("pool", pool_name_cfg)
    cust_disc = get_disc("custody", cust_name_cfg)

    # Query Pool accounts
    pools: List[dict] = []
    try:
        res_pool = _rpc("getProgramAccounts", [program_id, _filter_params(pool_disc)])
        for it in (res_pool or []):
            pools.append({"pubkey": it.get("pubkey")})
    except Exception as e:
        return {"ok": False, "error": f"Pool GPA failed: {e}"}

    # Query Custody accounts
    custodies: List[dict] = []
    try:
        res_cust = _rpc("getProgramAccounts", [program_id, _filter_params(cust_disc)])
        for it in (res_cust or []):
            custodies.append({"pubkey": it.get("pubkey")})
    except Exception as e:
        return {"ok": False, "error": f"Custody GPA failed: {e}"}

    return {
        "ok": True,
        "programId": program_id,
        "accountsFromIDL": idl_accounts,
        "usingAccountNames": {"pool": pool_name_cfg, "custody": cust_name_cfg},
        "poolsCount": len(pools),
        "custodiesCount": len(custodies),
        "pools": pools,
        "custodies": custodies,
        "note": "pubkey-only fallback with configurable discriminators; set PERPS_* envs if needed."
    }
