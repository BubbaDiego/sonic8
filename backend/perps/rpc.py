
import os, asyncio
from typing import List, Tuple, Any, Callable
from dotenv import load_dotenv
from solana.rpc.async_api import AsyncClient
from solana.exceptions import SolanaRpcException
from .constants import PROJECT_ROOT

DEFAULT_RPC_FALLBACKS = ["https://api.mainnet-beta.solana.com"]

def info(s): print(f"   ℹ️  {s}", flush=True)
def warn(s): print(f"   ⚠️  {s}", flush=True)

def load_endpoints() -> List[str]:
    env_path = PROJECT_ROOT / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
    primary = os.getenv("RPC_URL", "").strip()
    extras  = [x.strip() for x in os.getenv("RPC_LIST", "").split(",") if x.strip()]
    endpoints: List[str] = []
    seen = set()
    def add(u: str):
        if u and u not in seen:
            seen.add(u); endpoints.append(u)
    add(primary)
    for e in extras: add(e)
    for f in DEFAULT_RPC_FALLBACKS: add(f)
    info(f"RPC endpoints in order: {endpoints}")
    if not endpoints: raise SystemExit("❌ No RPC_URL configured in .env")
    return endpoints

async def new_client(url: str) -> AsyncClient:
    return AsyncClient(url, commitment=None)

def is_rate_limit(exc: Exception) -> bool:
    s = repr(exc)
    return ("429" in s) or ("Too Many Requests" in s) or ("rate" in s.lower())

async def rpc_call_with_rotation(op_factory: Callable[[str], Any],
                                 endpoints: List[str],
                                 start_idx: int = 0,
                                 attempts_per_endpoint: int = 2,
                                 sleep_base: float = 0.35) -> Tuple[int, Any]:
    if not endpoints: raise SystemExit("❌ No RPC endpoints")
    n = len(endpoints); idx = start_idx % n; last_exc = None
    for _ in range(n):
        url = endpoints[idx]
        for att in range(attempts_per_endpoint):
            try:
                return idx, await op_factory(url)
            except Exception as e:
                last_exc = e
                if is_rate_limit(e) or isinstance(e, SolanaRpcException):
                    warn(f"RPC @ {url} error {e!r} (attempt {att+1}/{attempts_per_endpoint})")
                    await asyncio.sleep(sleep_base * (2 ** att)); continue
                warn(f"RPC @ {url} non-429 error {e!r} — rotating")
                break
        idx = (idx + 1) % n
    raise last_exc if last_exc else RuntimeError("RPC rotation failed")
