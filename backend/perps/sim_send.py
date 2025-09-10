
from typing import List, Tuple, Dict, Any, Optional
from solana.transaction import Transaction
from solana.rpc.types import TxOpts
from .rpc import new_client, rpc_call_with_rotation
from .anchor_raw import build_raw_instruction, compute_budget_ixs

def info(s): print(f"   ℹ️  {s}", flush=True)
def warn(s): print(f"   ⚠️  {s}", flush=True)

async def simulate_only_raw(kp, idl_path, ix_name: str, params_typed: Dict[str, Tuple[str, Any]], accounts_camel: Dict[str, Any], endpoints: List[str], start_idx: int=0) -> Tuple[Optional[List[str]], int]:
    async def build_and_sim(url: str):
        client = await new_client(url)
        try:
            ix = build_raw_instruction(idl_path, ix_name, params_typed, accounts_camel)
            bh = await client.get_latest_blockhash()
            tmp = Transaction(fee_payer=kp.pubkey(), recent_blockhash=bh.value.blockhash)
            for b in compute_budget_ixs(): tmp.add(b)
            tmp.add(ix)
            sim = await client.simulate_transaction(tmp, sig_verify=False)
            logs = getattr(getattr(sim,"value",None),"logs",None)
            return client, (list(logs) if logs else [])
        except Exception:
            await client.close(); raise
    idx, (client, logs) = await rpc_call_with_rotation(lambda url: build_and_sim(url), endpoints=endpoints, start_idx=start_idx)
    if logs: [print(l) for l in logs]
    await client.close()
    return logs, idx

async def simulate_and_send_raw(kp, idl_path, ix_name: str, params_typed: Dict[str, Tuple[str, Any]], accounts_camel: Dict[str, Any], endpoints: List[str], start_idx: int=0) -> Optional[str]:
    async def build_and_sim(url: str):
        client = await new_client(url)
        try:
            ix = build_raw_instruction(idl_path, ix_name, params_typed, accounts_camel)
            bh = await client.get_latest_blockhash()
            tmp = Transaction(fee_payer=kp.pubkey(), recent_blockhash=bh.value.blockhash)
            for b in compute_budget_ixs(): tmp.add(b)
            tmp.add(ix)
            sim = await client.simulate_transaction(tmp, sig_verify=False)
            return client, ix, sim
        except Exception:
            await client.close(); raise
    idx, (client, ix, sim) = await rpc_call_with_rotation(lambda url: build_and_sim(url), endpoints=endpoints, start_idx=start_idx)
    val = getattr(sim,"value",None)
    if val and getattr(val,"logs",None):
        info("raw simulate logs:"); [print(x) for x in val.logs]
    if getattr(val,"err",None): warn(f"raw simulate err: {val.err}")
    async def send_on(url: str):
        c = client if url == endpoints[idx] else await new_client(url)
        try:
            recent = await c.get_latest_blockhash()
            tx = Transaction(fee_payer=kp.pubkey(), recent_blockhash=recent.value.blockhash)
            for b in compute_budget_ixs(): tx.add(b)
            tmp_ix = build_raw_instruction(idl_path, ix_name, params_typed, accounts_camel)
            tx.add(tmp_ix)
            sig = await c.send_transaction(tx, kp, opts=TxOpts(skip_preflight=False))
            await c.confirm_transaction(sig.value)
            if c is not client: await c.close()
            return sig.value
        except Exception:
            if c is not client: await c.close()
            raise
    try:
        sig = await send_on(endpoints[idx]); await client.close(); return sig
    except Exception as e:
        warn(f"raw send error @ {endpoints[idx]}: {e!r}"); await client.close()
    for r in range(1,len(endpoints)):
        j = (idx+r) % len(endpoints)
        try:
            _, sig_val = await rpc_call_with_rotation(lambda url: send_on(url), endpoints=endpoints, start_idx=j, attempts_per_endpoint=1)
            return sig_val
        except Exception as e:
            warn(f"raw send error @ {endpoints[j]}: {e!r}")
    return None
