from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional

from solders.pubkey import Pubkey

from backend.services.perps.raw_rpc import get_program_id, get_idl_account_names
from backend.services.perps.config import get_disc, get_account_name
from backend.services.solana_rpc import get_program_accounts as gpa_cached

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

_CACHE: Dict[str, Dict[str, str]] = {}
_SUMMARY_CACHE: Optional[Dict[str, Any]] = None

_B58_ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58encode(data: bytes) -> str:
    n = int.from_bytes(data, "big")
    if n == 0:
        res = _B58_ALPH[0]
    else:
        chars: List[str] = []
        while n:
            n, r = divmod(n, 58)
            chars.append(_B58_ALPH[r])
        res = "".join(reversed(chars))
    leading = 0
    for ch in data:
        if ch == 0:
            leading += 1
        else:
            break
    return (_B58_ALPH[0] * leading) + res


def _decode_account_data(item: Dict[str, Any]) -> Optional[bytes]:
    account = item.get("account") or {}
    data = account.get("data")
    if isinstance(data, list) and data and isinstance(data[0], str):
        try:
            return base64.b64decode(data[0])
        except Exception:
            return None
    if isinstance(data, dict):
        encoded = data.get("encoded")
        if isinstance(encoded, str):
            try:
                return base64.b64decode(encoded)
            except Exception:
                return None
    return None


def _pubkey_from_slice(raw: Optional[bytes], offset: int) -> Optional[str]:
    if not raw or len(raw) < offset + 32:
        return None
    chunk = raw[offset:offset + 32]
    try:
        return str(Pubkey.from_bytes(chunk))
    except Exception:
        # fallback to base58 if solders conversion fails
        return _b58encode(chunk)


def _extract_field(entry: Dict[str, Any], keys: List[str]) -> Optional[str]:
    for key in keys:
        value = entry.get(key)
        if value:
            return str(value)
    return None


def _custody_pool(entry: Dict[str, Any]) -> Optional[str]:
    return _extract_field(entry, ["pool", "poolAddress", "pool_pubkey", "poolPubkey"])


def _filter_params_b58(disc: bytes) -> Dict[str, Any]:
    return {
        "encoding": "base64",
        "commitment": "confirmed",
        "filters": [{"memcmp": {"offset": 0, "bytes": _b58encode(disc)}}],
    }


def list_markets_sync() -> Dict[str, Any]:
    global _SUMMARY_CACHE

    program_id = get_program_id()
    idl_accounts = get_idl_account_names()

    pool_name_cfg = get_account_name("pool", "Pool")
    cust_name_cfg = get_account_name("custody", "Custody")
    pool_disc = get_disc("pool", pool_name_cfg)
    cust_disc = get_disc("custody", cust_name_cfg)

    pools: List[Dict[str, Any]] = []
    try:
        res_pool = gpa_cached(program_id, _filter_params_b58(pool_disc)) or []
        for item in res_pool:
            pools.append({"pubkey": item.get("pubkey")})
    except Exception as exc:
        return {
            "ok": False,
            "error": f"Pool GPA failed: {exc}",
            "programId": program_id,
            "accountsFromIDL": idl_accounts,
            "usingAccountNames": {"pool": pool_name_cfg, "custody": cust_name_cfg},
        }

    custodies: List[Dict[str, Any]] = []
    try:
        res_cust = gpa_cached(program_id, _filter_params_b58(cust_disc)) or []
        for item in res_cust:
            entry: Dict[str, Any] = {"pubkey": item.get("pubkey")}
            raw = _decode_account_data(item)
            pool_addr = _pubkey_from_slice(raw, 8)
            if pool_addr:
                entry["pool"] = pool_addr
            mint = _pubkey_from_slice(raw, 8 + 32)
            if mint:
                entry["mint"] = mint
            token_account = _pubkey_from_slice(raw, 8 + 32 + 32)
            if token_account:
                entry["tokenAccount"] = token_account
            decimals_offset = 8 + (32 * 3)
            if raw and len(raw) > decimals_offset:
                entry["decimals"] = raw[decimals_offset]
            custodies.append(entry)
    except Exception as exc:
        return {
            "ok": False,
            "error": f"Custody GPA failed: {exc}",
            "programId": program_id,
            "accountsFromIDL": idl_accounts,
            "usingAccountNames": {"pool": pool_name_cfg, "custody": cust_name_cfg},
        }

    by_pool: Dict[str, Dict[str, Any]] = {}
    for pool in pools:
        addr = _extract_field(pool, ["address", "pubkey", "pool"])
        if addr and addr not in by_pool:
            by_pool[addr] = {"pool": addr, "custodies": []}
    for custody in custodies:
        pool_addr = _custody_pool(custody)
        if pool_addr:
            by_pool.setdefault(pool_addr, {"pool": pool_addr, "custodies": []})
            by_pool[pool_addr]["custodies"].append(custody)

    result: Dict[str, Any] = {
        "ok": True,
        "programId": program_id,
        "accountsFromIDL": idl_accounts,
        "usingAccountNames": {"pool": pool_name_cfg, "custody": cust_name_cfg},
        "poolsCount": len(pools),
        "custodiesCount": len(custodies),
        "pools": pools,
        "custodies": custodies,
        "byPool": by_pool,
        "note": "pubkey+mint view via base58 memcmp; set PERPS_* envs if IDL names differ.",
    }

    _SUMMARY_CACHE = result
    return result


def _markets_summary() -> Dict[str, Any]:
    global _SUMMARY_CACHE
    if _SUMMARY_CACHE:
        return _SUMMARY_CACHE

    try:
        from backend.services.perps.client import markets_summary  # type: ignore

        summary = markets_summary()
        if isinstance(summary, dict):
            _SUMMARY_CACHE = summary
            return summary
    except Exception:
        pass

    try:
        from backend.services.perps.client import list_pools_and_custodies  # type: ignore

        summary = list_pools_and_custodies()
        if isinstance(summary, dict):
            _SUMMARY_CACHE = summary
            return summary
    except Exception:
        pass

    summary = list_markets_sync()
    if isinstance(summary, dict) and summary.get("ok"):
        _SUMMARY_CACHE = summary
    return summary


def resolve_market(market: str) -> Dict[str, str]:
    mkey = (market or "").upper()
    if not mkey:
        raise ValueError("market name required")
    if mkey in _CACHE:
        return _CACHE[mkey]

    summary = _markets_summary()
    if not isinstance(summary, dict):
        raise RuntimeError("Perps markets summary unavailable")
    if summary.get("ok") is False:
        raise RuntimeError(summary.get("error") or "Perps markets summary unavailable")

    pools = summary.get("pools") or []
    custodies = summary.get("custodies") or []

    def pool_addr_from_entry(entry: Any) -> Optional[str]:
        if isinstance(entry, str):
            return entry
        if isinstance(entry, dict):
            return _extract_field(entry, ["address", "pubkey", "pool"])
        return None

    pool_addr: Optional[str] = None
    base_custody: Optional[Dict[str, Any]] = None
    quote_custody: Optional[Dict[str, Any]] = None

    for pool_entry in pools:
        addr = pool_addr_from_entry(pool_entry)
        if not addr:
            continue
        related = [c for c in custodies if _custody_pool(c) == addr]
        base_candidate = next((c for c in related if c.get("mint") == SOL_MINT), None)
        quote_candidate = next((c for c in related if c.get("mint") == USDC_MINT), None)
        if base_candidate and quote_candidate:
            pool_addr = addr
            base_custody = base_candidate
            quote_custody = quote_candidate
            break

    if not pool_addr:
        pool_addr = pool_addr_from_entry(pools[0]) if pools else None

    by_market = summary.get("byMarket") or {}
    if isinstance(by_market, dict):
        market_entry = by_market.get(mkey)
        if isinstance(market_entry, dict):
            pool_addr = market_entry.get("pool") or pool_addr
            if not base_custody:
                cust_list = market_entry.get("custodies") or []
                if isinstance(cust_list, list):
                    base_custody = next((c for c in cust_list if isinstance(c, dict) and c.get("mint") == SOL_MINT), base_custody)
                    quote_custody = next((c for c in cust_list if isinstance(c, dict) and c.get("mint") == USDC_MINT), quote_custody)
            oracle_hint = market_entry.get("oracle")
        else:
            oracle_hint = None
    else:
        oracle_hint = None

    if not base_custody:
        filtered = [c for c in custodies if not pool_addr or _custody_pool(c) == pool_addr]
        if filtered:
            base_custody = next((c for c in filtered if c.get("mint") == SOL_MINT), None) or filtered[0]

    if not quote_custody:
        quote_custody = next(
            (c for c in custodies if (not pool_addr or _custody_pool(c) == pool_addr) and c.get("mint") == USDC_MINT),
            None,
        )
    if not quote_custody:
        quote_custody = next((c for c in custodies if c.get("mint") == USDC_MINT), None)
    if not quote_custody:
        raise RuntimeError("USDC custody not found; ensure USDC mint is present in markets summary")

    if not pool_addr:
        raise RuntimeError("Pool address not found in markets summary")
    if not base_custody:
        raise RuntimeError("Custodies not found in markets summary")

    base_addr = _extract_field(base_custody, ["address", "pubkey", "custody"])
    quote_addr = _extract_field(quote_custody, ["address", "pubkey", "custody"])
    if not base_addr or not quote_addr:
        raise RuntimeError("Custody addresses not found in markets summary")

    base_mint = base_custody.get("mint") or SOL_MINT
    quote_mint = quote_custody.get("mint") or USDC_MINT

    oracle = summary.get("oracle") or oracle_hint
    if not oracle:
        by_pool = summary.get("byPool")
        if isinstance(by_pool, dict):
            oracle = (by_pool.get(pool_addr) or {}).get("oracle")

    result = {
        "pool": str(pool_addr),
        "oracle": str(oracle) if oracle else "",
        "custody_base": str(base_addr),
        "custody_quote": str(quote_addr),
        "base_mint": str(base_mint),
        "quote_mint": str(quote_mint),
    }

    _CACHE[mkey] = result
    return result


def resolve_extra_account(market: str, name: str) -> str:
    raise KeyError(f"Missing mapping for extra account '{name}' in market '{market}'")
