# backend/services/perps/markets.py
from __future__ import annotations

import hashlib
from typing import Dict, List

from backend.services.perps.raw_rpc import _rpc, get_program_id, get_idl_account_names
from backend.services.perps.config import get_disc, get_account_name


# ---------- base58 (tiny local encoder; no extra dependency) ----------
_B58_ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def _b58encode(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    if n == 0:
        res = _B58_ALPH[0]
    else:
        res_chars = []
        while n > 0:
            n, r = divmod(n, 58)
            res_chars.append(_B58_ALPH[r])
        res = "".join(reversed(res_chars))
    # preserve leading zero bytes as '1'
    leading = 0
    for ch in b:
        if ch == 0:
            leading += 1
        else:
            break
    return (_B58_ALPH[0] * leading) + res


def _filter_params_b58(disc: bytes) -> dict:
    """
    getProgramAccounts params with memcmp filter on discriminator (offset=0),
    encoding requirement for 'bytes' is **base58** (not base64).
    """
    return {
        "encoding": "base64",            # response encoding; fine to keep base64
        "commitment": "confirmed",
        "filters": [
            {"memcmp": {"offset": 0, "bytes": _b58encode(disc)}}
        ]
    }


def list_markets_sync() -> Dict[str, object]:
    """
    SAFE, FAST: return ONLY pubkeys of Pool and Custody accounts using
    server-side memcmp filter on the Anchor discriminator (base58).
    No Anchor decode here; this keeps us resilient until IDL is canonical.
    """
    program_id = get_program_id()
    idl_accounts = get_idl_account_names()

    # allow overrides via env (PERPS_POOL_ACCOUNT_NAME / PERPS_POOL_DISC etc.)
    pool_name_cfg = get_account_name("pool", "Pool")
    cust_name_cfg = get_account_name("custody", "Custody")
    pool_disc = get_disc("pool", pool_name_cfg)
    cust_disc = get_disc("custody", cust_name_cfg)

    # Query Pool accounts (filtered at RPC)
    pools: List[dict] = []
    try:
        res_pool = _rpc("getProgramAccounts", [program_id, _filter_params_b58(pool_disc)])
        for it in (res_pool or []):
            pools.append({"pubkey": it.get("pubkey")})
    except Exception as e:
        return {"ok": False, "error": f"Pool GPA failed: {e}"}

    # Query Custody accounts (filtered at RPC)
    custodies: List[dict] = []
    try:
        res_cust = _rpc("getProgramAccounts", [program_id, _filter_params_b58(cust_disc)])
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
        "note": "pubkey-only fallback with base58 memcmp; set PERPS_* envs if IDL names differ.",
    }


from typing import Dict as _Dict

# TODO(bubba): fill these from confirmed Jupiter Perps addresses.
# Keys SHOULD match IDL account names wherever possible.
_MARKETS: _Dict[str, _Dict[str, str]] = {
    "SOL-PERP": {
        "pool":          "ReplaceWithPoolPubkey",
        "oracle":        "ReplaceWithOraclePubkey",
        "custody_base":  "ReplaceWithSOLCustodyPubkey",
        "custody_quote": "ReplaceWithUSDCCustodyPubkey",
        "custody":       "ReplaceWithSOLCustodyPubkey",
        "collateralCustody": "ReplaceWithCollateralCustodyPubkey",
        "custodyDovesPriceAccount": "ReplaceWithCustodyDovesPricePubkey",
        "custodyPythnetPriceAccount": "ReplaceWithCustodyPythPricePubkey",
        "collateralCustodyDovesPriceAccount": "ReplaceWithCollateralDovesPricePubkey",
        "collateralCustodyPythnetPriceAccount": "ReplaceWithCollateralPythPricePubkey",
        "collateralCustodyTokenAccount": "ReplaceWithCollateralTokenAccountPubkey",
        "input_mint": "ReplaceWithInputMintPubkey",
        "referral": "ReplaceWithReferralPubkey",
    },
    "BTC-PERP": {
        "pool":          "ReplaceWithPoolPubkey",
        "oracle":        "ReplaceWithOraclePubkey",
        "custody_base":  "ReplaceWithBTCCustodyPubkey",
        "custody_quote": "ReplaceWithUSDCCustodyPubkey",
        "custody":       "ReplaceWithBTCCustodyPubkey",
        "collateralCustody": "ReplaceWithCollateralCustodyPubkey",
        "custodyDovesPriceAccount": "ReplaceWithCustodyDovesPricePubkey",
        "custodyPythnetPriceAccount": "ReplaceWithCustodyPythPricePubkey",
        "collateralCustodyDovesPriceAccount": "ReplaceWithCollateralDovesPricePubkey",
        "collateralCustodyPythnetPriceAccount": "ReplaceWithCollateralPythPricePubkey",
        "collateralCustodyTokenAccount": "ReplaceWithCollateralTokenAccountPubkey",
        "input_mint": "ReplaceWithInputMintPubkey",
        "referral": "ReplaceWithReferralPubkey",
    },
    "ETH-PERP": {
        "pool":          "ReplaceWithPoolPubkey",
        "oracle":        "ReplaceWithOraclePubkey",
        "custody_base":  "ReplaceWithETHCustodyPubkey",
        "custody_quote": "ReplaceWithUSDCCustodyPubkey",
        "custody":       "ReplaceWithETHCustodyPubkey",
        "collateralCustody": "ReplaceWithCollateralCustodyPubkey",
        "custodyDovesPriceAccount": "ReplaceWithCustodyDovesPricePubkey",
        "custodyPythnetPriceAccount": "ReplaceWithCustodyPythPricePubkey",
        "collateralCustodyDovesPriceAccount": "ReplaceWithCollateralDovesPricePubkey",
        "collateralCustodyPythnetPriceAccount": "ReplaceWithCollateralPythPricePubkey",
        "collateralCustodyTokenAccount": "ReplaceWithCollateralTokenAccountPubkey",
        "input_mint": "ReplaceWithInputMintPubkey",
        "referral": "ReplaceWithReferralPubkey",
    },
}


def resolve_market(market: str) -> _Dict[str, str]:
    m = _MARKETS.get(market.upper())
    if not m:
        raise ValueError(f"Unknown perps market: {market}")
    return m


def resolve_extra_account(market: str, name: str) -> str:
    """
    If the IDL lists additional required accounts on an instruction, add them to _MARKETS[market]
    with keys that match the IDL 'accounts' entries. If unknown, raise so we fill the registry.
    """
    m = _MARKETS.get(market.upper()) or {}
    if name in m:
        return m[name]
    raise KeyError(
        f"No mapping for extra account '{name}' on market '{market}'. "
        f"Add it to backend/services/perps/markets.py _MARKETS[{market!r}]['{name}']."
    )
