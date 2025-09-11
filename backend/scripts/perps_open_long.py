#!/usr/bin/env python
# -*- coding: utf-8 -*-

# --- make "perps" package resolvable when running this file directly ---
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # adds ...\backend to sys.path

import argparse
import asyncio
import json
import time
from typing import Optional, Tuple

from solders.keypair import Keypair
from solders.pubkey import Pubkey

# Split-module imports
from perps.constants import (
    IDL_PATH,
    USDC_MINT,
    CUSTODY_SOL,
    CUSTODY_USDC,
    POOL,
    LAMPORTS_PER_SOL,
    MIN_SOL_LAMPORTS,
    PERPS_PROGRAM_ID,
    TOKEN_PROGRAM,
    ASSOCIATED_TOKEN_PROGRAM,
    SYSTEM_PROGRAM,
)
from perps.rpc import load_endpoints, new_client, rpc_call_with_rotation
from perps.idl import ensure_idl, _load_idl_json, _find_ix_json
from perps.pdas import (
    derive_position_request_pda,
    derive_event_authority,
    derive_perpetuals_pda,
    derive_ata,
    derive_position_pda_v1,
    derive_position_pda_v2,
    derive_position_pda_v3,
)
from perps.sim_send import simulate_only_raw, simulate_and_send_raw
from perps.seeds_fix import parse_seeds_violation


# ---------- tiny log helpers ----------
def say(s): print(f"\n🟠 {s} …", flush=True)
def done(s="done"): print(f"   ✅ {s}", flush=True)
def info(s): print(f"   ℹ️  {s}", flush=True)
def warn(s): print(f"   ⚠️  {s}", flush=True)


# ---------- local utils ----------
def _camel_to_snake(name: str) -> str:
    out = []
    for ch in name:
        out.append("_" + ch.lower() if ch.isupper() else ch)
    s = "".join(out)
    return s[1:] if s.startswith("_") else s


def build_params_from_idl_json(
    idl_json: dict,
    ix_name: str,
    size_usd_6dp: int,
    collateral_atoms: int,
    max_price_usd_6dp: int,
    counter_value: int,
) -> dict[str, tuple[str, int]]:
    ix = _find_ix_json(idl_json, ix_name) or _find_ix_json(idl_json, _camel_to_snake(ix_name))
    if not ix:
        raise SystemExit(f"❌ IDL JSON has no instruction named {ix_name}")

    args = ix.get("args", [])
    if not args:
        return {}

    # Find a defined struct in arg0
    fields = None
    t = args[0].get("type", {})
    defined = t.get("defined")
    if defined:
        for tp in idl_json.get("types", []) or []:
            if tp.get("name") == defined and tp.get("type", {}).get("kind") == "struct":
                fields = tp.get("type", {}).get("fields", [])
                break
        info(f"IDL JSON params '{args[0].get('name')}' → type '{defined}' fields: {[f['name'] for f in (fields or [])]}")
    params: dict[str, tuple[str, int]] = {}
    if fields:
        for f in fields:
            nm = f.get("name"); nm_low = nm.lower()
            fty = f.get("type", {})
            if isinstance(fty, dict) and "defined" in fty:
                # enums as indices (e.g., side)
                params[nm] = ("enum_index", 0 if nm_low == "side" else 0)
            else:
                if "size" in nm_low and "usd" in nm_low:
                    params[nm] = ("u64", size_usd_6dp)
                elif "collateral" in nm_low and "delta" in nm_low:
                    params[nm] = ("u64", collateral_atoms)  # amount in inputMint atoms
                elif nm_low == "collateral_token_delta":
                    params[nm] = ("u64", collateral_atoms)
                elif "slippage" in nm_low:
                    params[nm] = ("u64", max_price_usd_6dp)
                elif "jupiter" in nm_low and "minimum" in nm_low:
                    params[nm] = ("u64", 0)
                elif nm_low == "counter":
                    params[nm] = ("u64", counter_value)
                elif "entireposition" in nm_low or "entire_position" in nm_low:
                    params[nm] = ("u8", 0)
                else:
                    params[nm] = ("u64", 0)
    else:
        params = {
            "sizeUsdDelta": ("u64", size_usd_6dp),
            "collateralTokenDelta": ("u64", collateral_atoms),
            "side": ("enum_index", 0),
            "priceSlippage": ("u64", max_price_usd_6dp),
            "jupiterMinimumOut": ("u64", 0),
            "counter": ("u64", counter_value),
        }
    return params


def parse_signer(signer_file: Path) -> Keypair:
    raw = signer_file.read_text(encoding="utf-8")
    kv: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            kv[k.strip().lower()] = v.strip()
        else:
            if " " in line and len(line.split()) >= 12:
                kv.setdefault("mnemonic", line)

    if "secret_b64" in kv:
        import base64
        raw = base64.b64decode(kv["secret_b64"])
        try:
            if raw and raw[:1] == b"[" and raw[-1:] == b"]":
                raw = bytes(json.loads(raw.decode()))
        except Exception:
            pass
        return Keypair.from_bytes(raw) if len(raw) == 64 else Keypair.from_seed(raw)

    if "mnemonic" in kv:
        import unicodedata, hashlib, hmac, struct
        m = unicodedata.normalize("NFKD", kv["mnemonic"].strip())
        s = "mnemonic" + unicodedata.normalize("NFKD", kv.get("mnemonic_passphrase", "") or "")
        seed = hashlib.pbkdf2_hmac("sha512", m.encode(), s.encode(), 2048, dklen=64)

        def hmac512(key, data): return hmac.new(key, data, hashlib.sha512).digest()
        I = hmac512(b"ed25519 seed", seed)
        k, c = I[:32], I[32:]

        def ckd_priv(k_par, c_par, i):
            if i < 0x80000000:
                raise ValueError("ed25519 hardened only")
            data = b"\x00" + k_par + struct.pack(">L", i)
            I = hmac512(c_par, data)
            return I[:32], I[32:]

        path = kv.get("derivation_path", "m/44'/501'/0'/0'")
        if path not in ("m", "m/"):
            for p in path[2:].split("/"):
                if not p:
                    continue
                idx = int(p[:-1] if p.endswith("'") else p, 10) | 0x80000000
                k, c = ckd_priv(k, c, idx)
        return Keypair.from_seed(k)

    raise SystemExit("❌ signer.txt needs secret_b64=... or mnemonic=...")


async def fix_seeds_then_send(
    kp: Keypair,
    ix_name: str,
    params_typed: dict[str, tuple[str, int]],
    accounts: dict[str, Pubkey],
    endpoints: list[str],
    start_idx: int,
    counter: int,
) -> Optional[str]:
    """Loop: simulate → parse 'Right:' → patch position/position_request → final send."""
    MAX_FIXES = 4
    idx_used = start_idx
    for _ in range(MAX_FIXES):
        logs, idx_used = await simulate_only_raw(kp, IDL_PATH, ix_name, params_typed, accounts, endpoints, start_idx=idx_used)
        acct_bad, right_key = parse_seeds_violation(logs or [])
        if not (acct_bad and right_key):
            break
        info(f"Seeds violation on {acct_bad}; program expects: {str(right_key)}")
        if acct_bad == "position":
            pos = right_key
            pr  = derive_position_request_pda(pos, counter)
            accounts.update({
                "position": pos,
                "positionRequest": pr,
                "positionRequestAta": derive_ata(pr, accounts["inputMint"]),
            })
        elif acct_bad == "position_request":
            pr = right_key
            accounts.update({
                "positionRequest": pr,
                "positionRequestAta": derive_ata(pr, accounts["inputMint"]),
            })
        else:
            warn(f"Unhandled seeds account '{acct_bad}' — continuing")

    return await simulate_and_send_raw(kp, IDL_PATH, ix_name, params_typed, accounts, endpoints, start_idx=idx_used)


def _get_val(params_typed: dict, key_candidates: list[str], default: int) -> Tuple[str, int]:
    for k in key_candidates:
        if k in params_typed:
            return k, int(params_typed[k][1])
    return key_candidates[0], default

def _set_val(params_typed: dict, key: str, val: int):
    kind = params_typed.get(key, ("u64", 0))[0]
    params_typed[key] = (kind, int(val))

def _parse_error_code(logs: list[str]) -> Optional[int]:
    for line in logs or []:
        if "Error Number:" in line:
            try: return int(line.split("Error Number:")[1].strip().split(".")[0].strip())
            except Exception: pass
        if "custom program error:" in line:
            try: return int(line.split("custom program error:")[1].strip(), 16)
            except Exception: pass
    return None

async def autotune_for_custody_limit(
    kp: Keypair,
    ix_name: str,
    params_typed: dict[str, tuple[str, int]],
    accounts: dict[str, Pubkey],
    endpoints: list[str],
    start_idx: int
) -> Optional[str]:
    size_key, size_val = _get_val(params_typed, ["sizeUsdDelta", "size_usd_delta"], 5_000_000)
    coll_key, coll_val = _get_val(params_typed, ["collateralTokenDelta", "collateral_token_delta", "collateralDelta"], 2_000_000)

    size_plan = [min(size_val, 5_000_000), 2_000_000, 1_000_000]  # $5 → $2 → $1
    coll_plan = [min(coll_val, 2_000_000), 1_000_000, 500_000]    # 2.0 → 1.0 → 0.5 (inputMint atoms)

    for i in range(len(size_plan)):
        new_size = size_plan[i]
        new_coll = coll_plan[i]
        _set_val(params_typed, size_key, new_size)
        _set_val(params_typed, coll_key, new_coll)
        say(f"Auto-tune for custody limit → sizeUsdDelta={new_size}  collateralTokenDelta={new_coll}")
        logs, idx_used = await simulate_only_raw(kp, IDL_PATH, ix_name, params_typed, accounts, endpoints, start_idx=start_idx)
        code = _parse_error_code(logs or [])
        if code == 6023:
            warn("Still hitting CustodyAmountLimit — trying smaller values …")
            continue
        sig = await simulate_and_send_raw(kp, IDL_PATH, ix_name, params_typed, accounts, endpoints, start_idx=idx_used)
        if sig:
            return sig
    return None


def _get_json(url: str) -> Optional[dict]:
    import json, urllib.request
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "curl/8.1.0",
                "Accept": "application/json",
                "Connection": "close",
                "Referer": "https://perps-api.jup.ag",
                "Origin": "https://perps-api.jup.ag",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        warn(f"Pool-info fetch failed: {e!r}")
        return None


# ---------- main flow ----------
async def amain():
    parser = argparse.ArgumentParser(
        description="Open a Jupiter Perps position on SOL (Market) with USDC input by default"
    )
    parser.add_argument("--side", choices=["long","short"], default="long")
    parser.add_argument("--size-usd", type=float, default=5.0)         # USD notional
    parser.add_argument("--input-usdc", type=float, default=2.0)       # amount of USDC you pay in (inputMint)
    parser.add_argument("--max-price", type=float, default=1000.0)
    parser.add_argument("--auto-switch-on-zero-liq", action="store_true",
                        help="If chosen side has 0 liquidity, automatically try the other side")
    parser.add_argument(
        "--signer-file",
        type=str,
        default=str(Path(__file__).resolve().parents[2] / "signer.txt"),
    )
    parser.add_argument("--skip-pool-preflight", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    endpoints = load_endpoints()

    say("Resolving signer")
    kp = parse_signer(Path(args.signer_file))

    idl = await ensure_idl()
    idl_json = _load_idl_json(IDL_PATH)

    size_6 = int(round(args.size_usd * 1_000_000))
    coll_6 = int(round(args.input_usdc * 1_000_000))  # inputMint=USDC atoms
    maxp_6 = int(round(args.max_price * 1_000_000))

    say("Preparing order parameters")
    info(f"Market    : SOL")
    info(f"Side      : {args.side}")
    info(f"Size USD  : {args.size_usd} (6dp={size_6})")
    info(f"Input amt : {args.input_usdc} USDC (atoms={coll_6})")
    info(f"Max price : {args.max_price} USD (6dp={maxp_6})")
    done("params ready")

    # Fee/rent sanity
    owner = kp.pubkey()
    client = await new_client(endpoints[0])
    lamports = (await client.get_balance(owner)).value
    await client.close()
    say("Preflight: SOL fee/rent check")
    info(f"have {lamports} lamports ({lamports / LAMPORTS_PER_SOL:.9f} SOL) need ≥ {MIN_SOL_LAMPORTS}")
    if lamports < MIN_SOL_LAMPORTS:
        raise SystemExit("❌ Not enough SOL for fees/rent.")
    done("fee/rent OK")

    # Pool capacity preflight (prevents 6023 thrash)
    SOL_MINT_STR = "So11111111111111111111111111111111111111112"
    side = args.side
    if not args.skip_pool_preflight:
        say("Checking pool capacity …")
        pool = _get_json(f"https://perps-api.jup.ag/v1/pool-info?mint={SOL_MINT_STR}")
        if pool is not None:
            try:
                long_liq  = int(pool.get("longAvailableLiquidity", "0"))
                short_liq = int(pool.get("shortAvailableLiquidity", "0"))
                info(f"longAvailableLiquidity:  {long_liq}")
                info(f"shortAvailableLiquidity: {short_liq}")
                if side == "long" and long_liq <= 0:
                    if args.auto-switch-on-zero-liq and short_liq > 0:
                        warn("No LONG liquidity; auto-switching to SHORT")
                        side = "short"
                    else:
                        raise SystemExit("❌ No LONG liquidity. Try --side short or try later.")
                if side == "short" and short_liq <= 0:
                    if args.auto-switch-on-zero-liq and long_liq > 0:
                        warn("No SHORT liquidity; auto-switching to LONG")
                        side = "long"
                    else:
                        raise SystemExit("❌ No SHORT liquidity. Try --side long or try later.")
            except Exception:
                warn("Could not parse pool-info — continuing without capacity guard.")

    # Pick instruction name
    ix_name = None
    for cand in ("createIncreasePositionMarketRequest","create_increase_position_market_request","createPositionRequest"):
        if _find_ix_json(idl_json, cand):
            ix_name = cand; break
    if not ix_name:
        say("Scanning IDL instructions for 'increase/position/request' …")
        from anchorpy import Provider, Wallet, Program
        idx, client = await rpc_call_with_rotation(lambda url: new_client(url), endpoints=endpoints, attempts_per_endpoint=1)
        program = Program(idl, PERPS_PROGRAM_ID, Provider(client, Wallet(kp)))
        for ix in program.idl.instructions:
            l = ix.name.lower()
            if "increase" in l and "position" in l and "request" in l:
                ix_name = ix.name
                break
        await client.close()
        if not ix_name:
            raise SystemExit("❌ Could not find increase position request instruction in IDL.")
    info(f"instruction: {ix_name}")

    # Params from IDL
    counter = int(time.time())
    params_typed = build_params_from_idl_json(idl_json, ix_name, size_6, coll_6, maxp_6, counter)

    # Build accounts by side (SOL market only)
    position = derive_position_pda_v1(owner, CUSTODY_SOL, CUSTODY_USDC)  # initial guess; seeds loop will fix
    position_request = derive_position_request_pda(position, counter)

    if side == "long":
        # LONG SOL:
        # - custody (market custody)        = SOL
        # - collateralCustody               = SOL (collateral == market for longs)
        # - inputMint                       = USDC (we pay USDC, program swaps)
        funding_account = derive_ata(owner, USDC_MINT)
        input_mint      = USDC_MINT
        position_custody        = CUSTODY_SOL
        collateral_custody_addr = CUSTODY_SOL
    else:
        # SHORT SOL:
        # - custody (market custody)        = SOL
        # - collateralCustody               = USDC
        # - inputMint                       = USDC
        funding_account = derive_ata(owner, USDC_MINT)
        input_mint      = USDC_MINT
        position_custody        = CUSTODY_SOL
        collateral_custody_addr = CUSTODY_USDC

    accounts = {
        "owner": owner,
        "pool": POOL,
        "custody": position_custody,
        "collateralCustody": collateral_custody_addr,
        "position": position,
        "positionRequest": position_request,
        "fundingAccount": funding_account,
        "perpetuals": derive_perpetuals_pda(),
        "positionRequestAta": derive_ata(position_request, input_mint),
        "inputMint": input_mint,
        "referral": owner,
        "tokenProgram": TOKEN_PROGRAM,
        "associatedTokenProgram": ASSOCIATED_TOKEN_PROGRAM,
        "systemProgram": SYSTEM_PROGRAM,
        "eventAuthority": derive_event_authority(),
        "program": PERPS_PROGRAM_ID,
    }

    say("IDL JSON params 'params' → sizeUsdDelta collateralTokenDelta side priceSlippage jupiterMinimumOut counter …")
    info("Dumping params & accounts …")
    print(json.dumps({k: (v[1] if isinstance(v, tuple) else v) for k, v in params_typed.items()}, indent=2))
    print(json.dumps({k: str(v) for k, v in accounts.items()}, indent=2))
    done("dumped")

    if args.dry_run:
        warn("dry-run enabled — not sending tx")
        return

    # Seeds-fix loop then send
    sig = await fix_seeds_then_send(
        kp=kp,
        ix_name=ix_name,
        params_typed=params_typed,
        accounts=accounts,
        endpoints=endpoints,
        start_idx=0,
        counter=counter,
    )

    # If still failing, see if it's 6023 and auto-tune
    if not sig:
        say("Checking for custody limit guard and auto-tuning if needed …")
        logs, idx_used = await simulate_only_raw(kp, IDL_PATH, ix_name, params_typed, accounts, endpoints, start_idx=0)
        code = _parse_error_code(logs or [])
        if code == 6023:
            sig = await autotune_for_custody_limit(kp, ix_name, params_typed, accounts, endpoints, start_idx=idx_used)

    # PDA probe fallback (rare now that mapping is corrected & we preflighted pool capacity)
    if not sig:
        def build_acc(pos_pda: Pubkey) -> dict[str, Pubkey]:
            pr = derive_position_request_pda(pos_pda, counter)
            a = dict(accounts)
            a.update({"position": pos_pda, "positionRequest": pr, "positionRequestAta": derive_ata(pr, input_mint)})
            return a

        for tag, candidate in (
            ("v1", derive_position_pda_v1(owner, CUSTODY_SOL, CUSTODY_USDC)),
            ("v2", derive_position_pda_v2(owner, POOL, CUSTODY_SOL, CUSTODY_USDC)),
            ("v3", derive_position_pda_v3(owner, POOL, CUSTODY_SOL, CUSTODY_USDC)),
        ):
            say(f"Simulating with position PDA {tag}: {str(candidate)}")
            sig = await simulate_and_send_raw(kp, IDL_PATH, ix_name, params_typed, build_acc(candidate), endpoints, start_idx=0)
            if sig:
                info(f"position PDA {tag} accepted; submitted → {sig}")
                break

    if not sig:
        raise SystemExit("❌ All strategies failed (pool preflight + seeds fix + auto-tune + probe). Likely no {side.upper()} capacity now. Try the other side or later.")

    done(f"submitted → {sig}")


if __name__ == "__main__":
    asyncio.run(amain())
