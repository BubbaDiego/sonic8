from __future__ import annotations
import json
from typing import Any, Dict, List, Tuple
from urllib.request import Request, urlopen

class MemcmpError(RuntimeError): ...

def _rpc_call(rpc_url: str, method: str, params: list, user_agent: str = "sonic7-gmsol-memcmp") -> Any:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    req  = Request(rpc_url, data=body, headers={"Content-Type":"application/json","User-Agent":user_agent})
    with urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if "error" in data:
        raise MemcmpError(f"{method} error: {data['error']}")
    return data["result"]

def memcmp_count(
    rpc_url: str,
    program_id: str,
    wallet_b58: str,
    owner_offset: int = 24,
    limit: int = 200,
    page: int = 1,
) -> Tuple[int, List[str]]:
    """
    Returns (#matches_on_page, sample_pubkeys_up_to_10)
    Uses getProgramAccounts with a single memcmp filter at owner_offset.
    """
    cfg = {
        "encoding":"base64",
        "commitment":"confirmed",
        "limit": limit,
        "page": page,
        "filters": [{"memcmp":{"offset": owner_offset, "bytes": wallet_b58}}],
    }
    res = _rpc_call(rpc_url, "getProgramAccounts", [program_id, cfg])
    if not isinstance(res, list):
        return 0, []
    sample = [a.get("pubkey") for a in res[:10] if isinstance(a, dict)]
    return len(res), sample

def memcmp_sweep(
    rpc_url: str,
    program_id: str,
    wallet_b58: str,
    offsets: List[int],
    limit: int = 200,
) -> List[Tuple[int, int]]:
    """
    Try multiple offsets; returns list of (offset, count_on_page1)
    """
    out: List[Tuple[int,int]] = []
    for off in offsets:
        try:
            n, _ = memcmp_count(rpc_url, program_id, wallet_b58, owner_offset=off, limit=limit, page=1)
            out.append((off, n))
        except Exception:
            out.append((off, -1))
    return out

def fetch_account_base64(rpc_url: str, pubkey: str) -> Dict[str, Any]:
    """
    getAccountInfo for pubkey; returns the RPC result 'value' dict (includes base64 data).
    """
    res = _rpc_call(rpc_url, "getAccountInfo", [pubkey, {"encoding":"base64"}])
    return res  # includes context + value
