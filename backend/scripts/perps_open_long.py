

import sys
from pathlib import Path as _PTH
# Ensure 'backend' (this file's parent) is on sys.path so 'perps' imports resolve
sys.path.insert(0, str(_PTH(__file__).resolve().parents[1]))

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse, asyncio, json, time
from pathlib import Path
from solders.keypair import Keypair
from perps.constants import IDL_PATH, USDC_MINT, CUSTODY_SOL, CUSTODY_USDC, POOL, LAMPORTS_PER_SOL, MIN_SOL_LAMPORTS
from perps.rpc import load_endpoints, new_client, rpc_call_with_rotation
from perps.idl import ensure_idl, _load_idl_json, _find_ix_json
from perps.pdas import derive_position_request_pda, derive_event_authority, derive_perpetuals_pda, derive_ata, derive_position_pda_v1, derive_position_pda_v2, derive_position_pda_v3
from perps.anchor_raw import build_raw_instruction, compute_budget_ixs
from perps.sim_send import simulate_only_raw, simulate_and_send_raw
from perps.seeds_fix import parse_seeds_violation

def say(s): print(f"\n🟠 {s} …", flush=True)
def done(s="done"): print(f"   ✅ {s}", flush=True)
def info(s): print(f"   ℹ️  {s}", flush=True)
def warn(s): print(f"   ⚠️  {s}", flush=True)

def _camel_to_snake(name: str) -> str:
    out=[]; 
    for ch in name: out.append("_"+ch.lower() if ch.isupper() else ch)
    s="".join(out); return s[1:] if s.startswith("_") else s

def build_params_from_idl_json(idl_json: dict, ix_name: str, size_usd_6dp: int, collateral_atoms: int, max_price_usd_6dp: int, counter_value: int):
    ix = _find_ix_json(idl_json, ix_name) or _find_ix_json(idl_json, _camel_to_snake(ix_name))
    args = ix.get("args", [])
    fields=None
    t = args[0].get("type", {}); defined=t.get("defined")
    if defined:
        for tp in idl_json.get("types", []) or []:
            if tp.get("name")==defined and tp.get("type",{}).get("kind")=="struct":
                fields = tp.get("type",{}).get("fields",[]); break
        info(f"IDL JSON params '{args[0].get('name')}' → type '{defined}' fields: {[f['name'] for f in (fields or [])]}")
    params={}
    if fields:
        for f in fields:
            nm=f.get("name"); nm_low=nm.lower(); fty=f.get("type",{})
            if isinstance(fty, dict) and "defined" in fty:
                params[nm]=("enum_index", 0 if nm_low=="side" else 0)
            else:
                if "size" in nm_low and "usd" in nm_low: params[nm]=("u64", size_usd_6dp)
                elif "collateral" in nm_low and "delta" in nm_low: params[nm]=("u64", collateral_atoms)
                elif nm_low=="collateral_token_delta": params[nm]=("u64", collateral_atoms)
                elif "slippage" in nm_low: params[nm]=("u64", max_price_usd_6dp)
                elif "jupiter" in nm_low and "minimum" in nm_low: params[nm]=("u64", 0)
                elif nm_low=="counter": params[nm]=("u64", counter_value)
                else: params[nm]=("u64", 0)
    else:
        params={"sizeUsdDelta":("u64",size_usd_6dp),"collateralTokenDelta":("u64",collateral_atoms),"side":("enum_index",0),"priceSlippage":("u64",max_price_usd_6dp),"jupiterMinimumOut":("u64",0),"counter":("u64",counter_value)}
    return params

def parse_signer(signer_file: Path) -> Keypair:
    raw = signer_file.read_text(encoding="utf-8")
    kv={}
    for line in raw.splitlines():
        line=line.strip()
        if not line or line.startswith("#"): continue
        if "=" in line:
            k,v=line.split("=",1); kv[k.strip().lower()]=v.strip()
        else:
            if " " in line and len(line.split())>=12: kv.setdefault("mnemonic", line)
    if "secret_b64" in kv:
        from perps.signer import keypair_from_b64
        return keypair_from_b64(kv["secret_b64"])
    elif "mnemonic" in kv:
        from perps.signer import keypair_from_mnemonic
        return keypair_from_mnemonic(kv["mnemonic"], kv.get("mnemonic_passphrase",""), kv.get("derivation_path","m/44'/501'/0'/0'"))
    else:
        raise SystemExit("❌ signer.txt needs secret_b64=... or mnemonic=...")

async def amain():
    parser = argparse.ArgumentParser(description="Open Jupiter Perps LONG SOL (Market) with USDC collateral")
    parser.add_argument("--size-usd", type=float, default=5.0)
    parser.add_argument("--collateral-usdc", type=float, default=2.0)
    parser.add_argument("--max-price", type=float, default=1000.0)
    parser.add_argument("--signer-file", type=str, default=str(Path(__file__).resolve().parents[2]/"signer.txt"))
    parser.add_argument("--dry-run", action="store_true"); parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    endpoints = load_endpoints()
    say("Resolving signer")
    kp = parse_signer(Path(args.signer_file))
    idl = await ensure_idl()

    size_6 = int(round(args.size_usd * 1_000_000))
    coll_6 = int(round(args.collateral_usdc * 1_000_000))
    maxp_6 = int(round(args.max_price * 1_000_000))

    say("Preparing order parameters")
    info(f"Action    : LONG SOL (market)")
    info(f"Size USD  : {args.size_usd} (6dp={size_6})")
    info(f"Collateral: {args.collateral_usdc} USDC (atoms={coll_6})")
    info(f"Max price : {args.max_price} USD (6dp={maxp_6})")
    done("params ready")

    owner = kp.pubkey()
    client = await new_client(endpoints[0])
    lamports = (await client.get_balance(owner)).value
    await client.close()
    if lamports < MIN_SOL_LAMPORTS:
        raise SystemExit("❌ Not enough SOL for fees/rent.")

    # Choose ix name
    idl_json = _load_idl_json(IDL_PATH)
    ix_name=None
    for cand in ("createIncreasePositionMarketRequest","create_increase_position_market_request","createPositionRequest"):
        if _find_ix_json(idl_json, cand): ix_name=cand; break
    if not ix_name:
        # worst case: pick first instruction that has 'increase' and 'request'
        from anchorpy import Program, Provider, Wallet
        idx, client = await rpc_call_with_rotation(lambda url: new_client(url), endpoints=endpoints, attempts_per_endpoint=1)
        program = Program(idl, PERPS_PROGRAM_ID, Provider(client, Wallet(kp)))
        names = [ix.name for ix in program.idl.instructions]
        for nm in names:
            l = nm.lower()
            if "increase" in l and "position" in l and "request" in l: ix_name=nm; break
        await client.close()
    info(f"IDL JSON params 'params' → sizeUsdDelta collateralTokenDelta side priceSlippage jupiterMinimumOut counter")

    counter = int(time.time())
    params_typed = build_params_from_idl_json(idl_json, ix_name, size_6, coll_6, maxp_6, counter)

    # initial guess: v1
    from perps.pdas import derive_position_pda_v1, derive_position_request_pda, derive_ata, derive_event_authority, derive_perpetuals_pda
    position = derive_position_pda_v1(owner, CUSTODY_SOL, CUSTODY_USDC)
    position_request = derive_position_request_pda(position, counter)

    accounts = {
        "owner": owner,
        "pool": POOL,
        "custody": CUSTODY_SOL,
        "collateralCustody": CUSTODY_USDC,
        "position": position,
        "positionRequest": position_request,
        "fundingAccount": derive_ata(owner, USDC_MINT),
        "perpetuals": derive_perpetuals_pda(),
        "positionRequestAta": derive_ata(position_request, USDC_MINT),
        "inputMint": USDC_MINT,
        "referral": owner,
        "tokenProgram": TOKEN_PROGRAM,
        "associatedTokenProgram": ASSOCIATED_TOKEN_PROGRAM,
        "systemProgram": SYSTEM_PROGRAM,
        "eventAuthority": derive_event_authority(),
        "program": PERPS_PROGRAM_ID,
    }

    say("IDL JSON params 'params' → sizeUsdDelta collateralTokenDelta side priceSlippage jupiterMinimumOut counter …")
    info("Dumping params & accounts …")
    print(json.dumps({k:(v[1] if isinstance(v,tuple) else v) for k,v in params_typed.items()}, indent=2))
    print(json.dumps({k:str(v) for k,v in accounts.items()}, indent=2))
    done("dumped")

    say("Falling back to RAW (simulate first, fix seeds if needed) …")
    logs, idx_used = await simulate_only_raw(kp, IDL_PATH, ix_name, params_typed, accounts, endpoints, start_idx=0)
    from perps.seeds_fix import parse_seeds_violation
    acct_bad, right_key = parse_seeds_violation(logs or [])
    if acct_bad and right_key:
        info(f"Seeds violation on {acct_bad}; program expects: {str(right_key)}")
        if acct_bad == "position":
            position = right_key
            position_request = derive_position_request_pda(position, counter)
            accounts.update({
                "position": position,
                "positionRequest": position_request,
                "positionRequestAta": derive_ata(position_request, USDC_MINT),
            })
        elif acct_bad == "position_request":
            position_request = right_key
            accounts.update({
                "positionRequest": position_request,
                "positionRequestAta": derive_ata(position_request, USDC_MINT),
            })
        sig = await simulate_and_send_raw(kp, IDL_PATH, ix_name, params_typed, accounts, endpoints, start_idx=idx_used)
    else:
        sig = await simulate_and_send_raw(kp, IDL_PATH, ix_name, params_typed, accounts, endpoints, start_idx=0)

    if not sig:
        from perps.pdas import derive_position_pda_v2, derive_position_pda_v3
        def build_acc(pos_pda: Pubkey):
            pr = derive_position_request_pda(pos_pda, counter)
            a = dict(accounts)
            a.update({"position": pos_pda, "positionRequest": pr, "positionRequestAta": derive_ata(pr, USDC_MINT)})
            return a
        for tag, candidate in (("v1", derive_position_pda_v1(owner, CUSTODY_SOL, CUSTODY_USDC)),
                               ("v2", derive_position_pda_v2(owner, POOL, CUSTODY_SOL, CUSTODY_USDC)),
                               ("v3", derive_position_pda_v3(owner, POOL, CUSTODY_SOL, CUSTODY_USDC))):
            say(f"Simulating with position PDA {tag}: {str(candidate)}")
            sig = await simulate_and_send_raw(kp, IDL_PATH, ix_name, params_typed, build_acc(candidate), endpoints, start_idx=0)
            if sig:
                info(f"position PDA {tag} accepted; submitted → {sig}")
                break

    if not sig:
        raise SystemExit("❌ All strategies failed (RAW + seeds fix + probe). See logs.")
    print(f"submitted → {sig}")

if __name__ == "__main__":
    asyncio.run(amain())