from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple, Optional
from urllib.request import Request, urlopen


class MemcmpError(RuntimeError):
    """Raised when the memcmp RPC path fails."""


def _rpc_call(
    rpc_url: str,
    method: str,
    params: list,
    user_agent: str = "sonic7-gmsol",
    timeout: float = 25.0,
) -> Any:
    body = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    ).encode("utf-8")
    req = Request(
        rpc_url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": user_agent},
    )
    with urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if "error" in data:
        raise MemcmpError(f"{method} error: {data['error']}")
    return data["result"]


def _is_helius(rpc_url: str) -> bool:
    return "helius-rpc.com" in (rpc_url or "").lower()


# -------------------------
# v1 helpers (generic nodes)
# -------------------------
def memcmp_count_v1(
    rpc_url: str,
    program_id: str,
    wallet_b58: str,
    owner_offset: int = 24,
    limit: int = 200,
    page: int = 1,
    data_size: Optional[int] = None,
    commitment: str = "confirmed",
) -> Tuple[int, List[str]]:
    """
    Returns (#matches_on_page, sample_pubkeys_up_to_10) using getProgramAccounts (provider-dependent pagination).
    """
    filters: List[Dict[str, Any]] = [{"memcmp": {"offset": owner_offset, "bytes": wallet_b58}}]
    if isinstance(data_size, int) and data_size > 0:
        filters.append({"dataSize": data_size})

    cfg = {
        "encoding": "base64",
        "commitment": commitment,
        "limit": max(1, int(limit)),
        "page": max(1, int(page)),
        "filters": filters,
    }
    res = _rpc_call(rpc_url, "getProgramAccounts", [program_id, cfg])
    if not isinstance(res, list):
        return 0, []
    sample = [a.get("pubkey") for a in res[:10] if isinstance(a, dict)]
    return len(res), sample


# -------------------------
# v2 helpers (Helius)
# -------------------------
def memcmp_find_any_v2(
    rpc_url: str,
    program_id: str,
    wallet_b58: str,
    owner_offset: int = 24,
    limit: int = 2000,
    max_pages: int = 100,
    data_size: Optional[int] = None,
    commitment: str = "confirmed",
) -> Tuple[int, List[str], Dict[str, Any]]:
    """
    Cursor-based scan using Helius getProgramAccountsV2. Returns (total_count, samples, debug).
    """
    filters: List[Dict[str, Any]] = [{"memcmp": {"offset": owner_offset, "bytes": wallet_b58}}]
    if isinstance(data_size, int) and data_size > 0:
        filters.append({"dataSize": data_size})

    base_cfg: Dict[str, Any] = {
        "encoding": "base64",
        "commitment": commitment,
        "limit": max(1, int(limit)),
        "filters": filters,
    }

    total = 0
    samples: List[str] = []
    pagination_key: Optional[str] = None

    dbg_pages: List[Dict[str, Any]] = []

    for page_idx in range(1, max_pages + 1):
        cfg = dict(base_cfg)
        if pagination_key:
            cfg["paginationKey"] = pagination_key
        res = _rpc_call(rpc_url, "getProgramAccountsV2", [program_id, cfg])

        # Helius format: {"accounts":[...], "paginationKey":"..."} or {"items":[...]}
        accts = []
        if isinstance(res, dict):
            accts = res.get("accounts") or res.get("items") or []
        elif isinstance(res, list):
            accts = res

        if not isinstance(accts, list):
            break

        # Debug page snapshot
        dbg_pages.append({
            "page_index": page_idx,
            "returned": len(accts),
            "paginationKey_in": pagination_key or "(none)",
            "has_next": bool(isinstance(res, dict) and res.get("paginationKey")),
        })

        total += len(accts)
        for a in accts:
            if isinstance(a, dict):
                pk = a.get("pubkey")
                if pk and len(samples) < 10:
                    samples.append(pk)

        pagination_key = None
        if isinstance(res, dict):
            pagination_key = res.get("paginationKey")

        if not pagination_key or len(samples) >= 10:
            break

    return total, samples, {
        "mode": "v2",
        "filters": filters,
        "limit": base_cfg["limit"],
        "pages": dbg_pages,
        "final_paginationKey": pagination_key or "(none)",
    }


def memcmp_sweep_v2(
    rpc_url: str,
    program_id: str,
    wallet_b58: str,
    offsets: List[int],
    limit: int = 2000,
    data_size: Optional[int] = None,
) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    for off in offsets:
        try:
            n, _, _dbg = memcmp_find_any_v2(
                rpc_url,
                program_id,
                wallet_b58,
                owner_offset=off,
                limit=limit,
                data_size=data_size,
            )
            out.append((off, n))
        except Exception:
            out.append((off, -1))
    return out


# -------------------------
# Utilities shared by menu
# -------------------------
def fetch_account_base64(rpc_url: str, pubkey: str) -> Dict[str, Any]:
    """
    getAccountInfo for pubkey; returns the RPC 'value' payload (context + value).
    """
    return _rpc_call(rpc_url, "getAccountInfo", [pubkey, {"encoding": "base64"}])


def memcmp_find(
    rpc_url: str,
    program_id: str,
    wallet_b58: str,
    owner_offset: int,
    limit: int,
    page: int,
    data_size: Optional[int],
    prefer_v2: bool,
) -> Tuple[int, List[str], str, Dict[str, Any]]:
    """
    Unified entry. Returns (count, samples, mode, debug).
    - If Helius endpoint and prefer_v2=True → V2 (cursor-based)
    - Else → V1
    """
    if prefer_v2 and _is_helius(rpc_url):
        n, sample, dbg = memcmp_find_any_v2(
            rpc_url=rpc_url,
            program_id=program_id,
            wallet_b58=wallet_b58,
            owner_offset=owner_offset,
            limit=limit,
            data_size=data_size,
        )
        return n, sample, "v2", dbg

    # fallback to V1 (page-limited)
    n, sample = memcmp_count_v1(
        rpc_url=rpc_url,
        program_id=program_id,
        wallet_b58=wallet_b58,
        owner_offset=owner_offset,
        limit=limit,
        page=page,
        data_size=data_size,
    )
    return n, sample, "v1", {
        "mode": "v1",
        "filters": [
            {"memcmp": {"offset": owner_offset, "bytes": wallet_b58}},
            *([{"dataSize": data_size}] if data_size else []),
        ],
        "limit": limit,
        "page": page,
    }
