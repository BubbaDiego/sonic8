from __future__ import annotations

import json
import os
import random
import time
from typing import Any, Dict, List

from urllib import error as urlerror
from urllib import request as urlrequest

from backend.config.rpc import helius_url, redacted


class RpcError(RuntimeError):
    pass


def _parse_urls() -> List[str]:
    """Build the RPC rotation based on available environment variables."""

    urls = [u.strip() for u in os.getenv("RPC_URLS", "").split(",") if u.strip()]
    if urls:
        return urls

    one = os.getenv("RPC_URL", "").strip()
    if one:
        return [one]

    try:
        return [helius_url()]
    except RuntimeError:
        pass

    # last resort: Solana public RPC (rate-limited)
    return ["https://api.mainnet-beta.solana.com"]


_RPC_URLS: List[str] = _parse_urls()
_RPC_MAX_RETRIES = max(1, int(os.getenv("RPC_MAX_RETRIES", "5")))
_HEADERS = {"User-Agent": "Cyclone/PerpsRPC"}


def _post_json(url: str, payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", **_HEADERS}
    req = urlrequest.Request(url, data=data, headers=headers, method="POST")
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
            return {"status": resp.getcode(), "text": text}
    except urlerror.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"status": exc.code, "text": body}
    except urlerror.URLError as exc:
        raise RpcError(str(exc)) from exc


def rpc_post(method: str, params: Any, timeout: float = 30.0) -> Any:
    """
    JSON-RPC POST with rotation + backoff.
    Retries on HTTP 429/5xx, DNS failures, connect timeouts.
    """

    attempt = 0
    err_last: Exception | None = None
    while attempt < _RPC_MAX_RETRIES:
        url = _RPC_URLS[attempt % len(_RPC_URLS)]
        try:
            payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            response = _post_json(url, payload, timeout)
            status = response["status"]
            if status == 429 or 500 <= status < 600:
                raise RpcError(f"HTTP {status} {response['text'][:200]}")
            if status != 200:
                raise RpcError(f"HTTP {status} {response['text'][:200]}")
            body = json.loads(response["text"] or "{}")
            if "error" in body:
                raise RpcError(f"RPC error {method}: {body['error']}")
            return body.get("result")
        except Exception as e:
            err_last = e
            sleep = min(2**attempt, 8) + random.random()
            print(
                f"[rpc] {method} via {redacted(url)} failed (attempt {attempt + 1}/{_RPC_MAX_RETRIES}): {e} "
                f"→ retry in {sleep:.1f}s"
            )
            time.sleep(sleep)
            attempt += 1
    raise RpcError(f"RPC exhausted for {method}: {err_last}")


_GPA_CACHE: Dict[str, tuple[float, Any]] = {}
_GPA_TTL = max(60, int(os.getenv("GPA_CACHE_TTL", "600")))


def _cache_key(program: str, cfg: Dict[str, Any]) -> str:
    return json.dumps({"p": program, "c": cfg}, sort_keys=True)


def get_program_accounts(program_id: str, cfg: Dict[str, Any]) -> Any:
    """
    Cached GPA with same rotation/backoff. TTL default 10min (configurable).
    """

    key = _cache_key(program_id, cfg)
    now = time.time()
    if key in _GPA_CACHE:
        ts, val = _GPA_CACHE[key]
        if now - ts < _GPA_TTL:
            return val

    result = rpc_post("getProgramAccounts", [program_id, cfg])
    _GPA_CACHE[key] = (now, result)
    return result
