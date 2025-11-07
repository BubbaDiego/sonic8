# -*- coding: utf-8 -*-
"""
Raydium Core — pick-list console (wallet + NFTs / Token-2022 aware)
- Uses project-root signer.txt via backend.services.signer_loader
- RPC from RPC_URL or backend.config.rpc.helius_url
- NFT heuristic:
    • Scan Token Program; scan Token-2022 if the constant is available
    • tokenAmount.decimals == 0 and tokenAmount.amount >= 1
    • (optional) confirm mint supply == 1, decimals == 0 → "strong"

Extra:
    • Menu item to call a TS helper using Raydium SDK to compute per-position value.

Run:
  py backend/core/raydium_core/console/raydium_console.py
"""

from __future__ import annotations

# -- ensure repo root on sys.path (works when run from anywhere) --
import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parents[4]))

from pathlib import Path

import json
import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple

# UTF-8 out on Windows
if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# --- project services ---
from backend.services.signer_loader import load_signer  # honors SONIC_SIGNER_PATH and root signer.txt
from backend.config import rpc as rpc_cfg  # helius_url()
from backend.core.raydium_core.services.nft_scanner import scan_owner_nfts
from backend.core.raydium_core.services.nft_valuation import value_owner_nfts
from backend.data.data_locker import DataLocker

# solana-py + solders
from solders.pubkey import Pubkey
from solana.rpc.api import Client as SolClient
from solana.rpc.types import TokenAccountOpts


# Program IDs — prefer canonical constants from spl.token.constants.
# If TOKEN_2022_PROGRAM_ID isn't available in your installed version, we skip Token-2022 gracefully.
try:
    from spl.token.constants import TOKEN_PROGRAM_ID as SPL_TOKEN_PROGRAM_ID  # type: ignore
    TOKEN_PROGRAM_ID: Pubkey = SPL_TOKEN_PROGRAM_ID  # already a Pubkey
except Exception:
    TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")

try:
    from spl.token.constants import TOKEN_2022_PROGRAM_ID as SPL_TOKEN_2022_PROGRAM_ID  # type: ignore
    TOKEN_2022_PROGRAM_ID: Optional[Pubkey] = SPL_TOKEN_2022_PROGRAM_ID  # may not exist in older libs
except Exception:
    TOKEN_2022_PROGRAM_ID = None  # not installed → skip Token-2022 scan


def _resolve_rpc_url() -> str:
    env = os.getenv("RPC_URL", "").strip()
    if env:
        return env
    try:
        return rpc_cfg.helius_url()
    except Exception:
        return "https://api.mainnet-beta.solana.com"


# ---------- Pretty UI ----------

def banner(title: str, subtitle: str = "") -> None:
    line = "─" * max(18, len(title) + 2, len(subtitle) + 2 if subtitle else 0)
    print(f"\n╭{line}╮")
    print(f"│ {title} │")
    if subtitle:
        print(f"│ {subtitle} │")
    print(f"╰{line}╯")


def ask(prompt: str, default: str = "") -> str:
    s = input(f"{prompt} [{default}]: ").strip()
    return s or default


def pause():
    input("\n↩️  Enter to continue...")


# ---------- Core ops ----------


def _run_ts_value_and_store(owner: str, mints: list[str]) -> int:
    ts_dir = Path("backend/core/raydium_core/ts").resolve()
    ts_entry = ts_dir / "value_raydium_positions.ts"
    ts_node = ts_dir / "node_modules" / ".bin" / ("ts-node.cmd" if os.name == "nt" else "ts-node")
    cmd = [
        str(ts_node),
        "--transpile-only",
        str(ts_entry),
        "--owner",
        owner,
        "--mints",
        ",".join(mints),
        "--emit-json",
    ]
    proc = subprocess.run(cmd, cwd=str(ts_dir), text=True, capture_output=True)
    out = (proc.stdout or "") + "\n" + (proc.stderr or "")

    payload = None
    for line in out.splitlines():
        if line.startswith("__JSON__:"):
            try:
                payload = json.loads(line.split(":", 1)[1])
            except Exception:
                pass

    if payload:
        try:
            dl = DataLocker.get_instance()
            if getattr(dl, "system", None) and hasattr(dl.system, "set_var"):
                dl.system.set_var("raydium_positions", payload.get("rows", []))
            if getattr(dl, "raydium", None):
                dl.raydium.upsert_from_ts_payload(owner, payload)
            print(f"   • persisted {len(payload.get('rows', []))} rows → system + DB")
        except Exception as e:
            print(f"   • persist note: {e}")
    else:
        print("   • no JSON payload from TS helper")

    return proc.returncode

def show_wallet(cl: SolClient):
    """
    Load wallet via your signer loader and print pubkey + SOL balance.
    """
    try:
        w = load_signer()
    except Exception:
        # Print a minimal hint that includes the first 200 chars of signer.txt
        signer_path = os.environ.get("SONIC_SIGNER_PATH", "signer.txt")
        sniff = ""
        try:
            with open(signer_path, "r", encoding="utf-8", errors="replace") as fh:
                raw = fh.read().strip()
            sniff = raw[:200].replace("\n", "\\n")
        except Exception:
            sniff = "(unable to read signer.txt)"
        print("\n❌ Signer load failed.")
        print("   Tip: signer.txt can be one of:")
        print("   • Solana id.json (array of 64 ints)")
        print("   • Base64 secret (32/64 bytes)")
        print("   • JSON object { mnemonic | phrase [, passphrase] } or { secretKey:[...] }")
        print("   • key=value text (mnemonic=..., alias: phrase=...)")
        print("   • Plain BIP39 mnemonic (12–24 words)")
        print(f"   signer path: {signer_path}")
        print(f"   first 200 chars: {sniff}")
        raise

    pub = w.pubkey()
    print(f"\n🔐 Wallet loaded: {pub}")
    try:
        bal = cl.get_balance(pub).value  # lamports
    except Exception:
        bal = int((cl.get_balance(pub) or {}).get("result", {}).get("value", 0))
    sol = float(bal) / 1e9
    print(f"   • Balance: {sol:.6f} SOL")
    return pub


def _fetch_owner_parsed(cl: SolClient, owner: Pubkey, program: Pubkey):
    """Prefer json-parsed; fall back to raw listing."""
    if hasattr(cl, "get_token_accounts_by_owner_json_parsed"):
        return ("parsed", cl.get_token_accounts_by_owner_json_parsed(
            owner, TokenAccountOpts(program_id=program)
        ))
    return ("raw", cl.get_token_accounts_by_owner(
        owner, TokenAccountOpts(program_id=program)
    ))


def _extract_candidates_from_parsed(resp) -> List[Tuple[str, str, int, int]]:
    """(mint, token_account, amount, decimals) from a jsonParsed response."""
    try:
        items = resp.value  # object form
        def _mint(i): return i.account.data.parsed["info"]["mint"]
        def _amt(i):  return int(i.account.data.parsed["info"]["tokenAmount"]["amount"])
        def _dec(i):  return int(i.account.data.parsed["info"]["tokenAmount"]["decimals"])
        def _pk(i):   return str(i.pubkey)
    except Exception:
        items = resp["result"]["value"]  # legacy dict form
        def _mint(i): return i["account"]["data"]["parsed"]["info"]["mint"]
        def _amt(i):  return int(i["account"]["data"]["parsed"]["info"]["tokenAmount"]["amount"])
        def _dec(i):  return int(i["account"]["data"]["parsed"]["info"]["tokenAmount"]["decimals"])
        def _pk(i):   return i["pubkey"]

    out: List[Tuple[str, str, int, int]] = []
    for it in items:
        try:
            out.append((_mint(it), _pk(it), _amt(it), _dec(it)))
        except Exception:
            continue
    return out


def _extract_candidates_from_raw(cl: SolClient, resp) -> List[Tuple[str, str, int, int]]:
    """From raw owner listing, fetch balance + mint per account."""
    try:
        items = resp.value
        accounts = [str(x.pubkey) for x in items]
    except Exception:
        items = resp["result"]["value"]
        accounts = [x["pubkey"] for x in items]

    out: List[Tuple[str, str, int, int]] = []
    for ta in accounts:
        try:
            bal = cl.get_token_account_balance(Pubkey.from_string(ta))
            try:
                v = bal.value
                amt = int(v.amount)
                dec = int(v.decimals)
            except Exception:
                v = bal["result"]["value"]
                amt = int(v["amount"])
                dec = int(v["decimals"])

            mint = None
            if hasattr(cl, "get_account_info_json_parsed"):
                ai = cl.get_account_info_json_parsed(Pubkey.from_string(ta))
                try:
                    mint = ai.value.data.parsed["info"]["mint"]
                except Exception:
                    pass
            if not mint:
                ai = cl.get_account_info(Pubkey.from_string(ta))
                try:
                    mint = ai["result"]["value"]["data"]["parsed"]["info"]["mint"]
                except Exception:
                    pass

            if mint:
                out.append((mint, ta, amt, dec))
        except Exception:
            continue
    return out


def _mint_supply(cl: SolClient, mint_str: str) -> Tuple[int, int] | None:
    """Return (amount, decimals) for the mint's total supply, or None if not available."""
    try:
        r = cl.get_token_supply(Pubkey.from_string(mint_str))
        try:
            v = r.value
            return int(v.amount), int(v.decimals)
        except Exception:
            v = r["result"]["value"]
            return int(v["amount"]), int(v["decimals"])
    except Exception:
        return None


def _scan_program(cl: SolClient, owner: Pubkey, program: Pubkey) -> List[Tuple[str, str, int, int]]:
    mode, resp = _fetch_owner_parsed(cl, owner, program)
    if mode == "parsed":
        return _extract_candidates_from_parsed(resp)
    return _extract_candidates_from_raw(cl, resp)


def list_suspected_nfts(cl: SolClient, owner: Pubkey, verbose: bool = True) -> List[Tuple[str, str, bool]]:
    """
    Return list of (mint, token_account, strong_flag)
      • strong_flag=True if mint supply == 1 and decimals == 0
    Heuristic: decimals == 0 and amount >= 1
    Scans Token Program; scans Token-2022 only if the constant exists.
    """
    totals = {}
    candidates: List[Tuple[str, str, int, int]] = []

    # Legacy Token Program
    rows = _scan_program(cl, owner, TOKEN_PROGRAM_ID)
    totals["Token"] = len(rows)
    for mint, ta, amt, dec in rows:
        if dec == 0 and amt >= 1:
            candidates.append((mint, ta, amt, dec))

    # Token-2022 (optional)
    if TOKEN_2022_PROGRAM_ID is not None:
        rows22 = _scan_program(cl, owner, TOKEN_2022_PROGRAM_ID)
        totals["Token-2022"] = len(rows22)
        for mint, ta, amt, dec in rows22:
            if dec == 0 and amt >= 1:
                candidates.append((mint, ta, amt, dec))
    else:
        totals["Token-2022"] = 0

    if verbose:
        print(f"   • Accounts scanned → Token: {totals.get('Token',0)}, Token-2022: {totals.get('Token-2022',0)}")
        print(f"   • NFT-ish candidates (dec=0, amt>=1): {len(candidates)}")

    # Validate supply==1 (when RPC supports it) to tag "strong" NFTs
    results: List[Tuple[str, str, bool]] = []
    for mint, ta, amt, dec in candidates:
        strong = False
        sup = _mint_supply(cl, mint)
        if sup is not None:
            s_amt, s_dec = sup
            strong = (s_dec == 0 and s_amt == 1)
        results.append((mint, ta, strong))
    return results


def print_nfts(nfts: List[Tuple[str, str, bool]]):
    if not nfts:
        print("   (no NFT-like token accounts found)")
        return
    for mint, ta, strong in nfts:
        mshort = f"{mint[:6]}…{mint[-6:]}"
        tshort = f"{ta[:6]}…{ta[-6:]}"
        star = "★" if strong else "•"
        print(f"   {star} 🖼️  mint {mshort}   • acct {tshort}")


# ---------- TS valuation launcher ----------


def _ts_valuation_command(owner_pubkey: str, mints: list[str]) -> tuple[Optional[list[str]], Path, dict[str, str]]:
    from shutil import which

    js_root = Path(__file__).resolve().parent.parent / "ts"
    script = js_root / "value_raydium_positions.ts"
    if not script.exists():
        print("❌ TS valuation script not found:", script)
        print(
            "   Create it via the TS helper snippet from the same CODEX block and run `npm i` in",
            js_root,
        )
        return None, js_root, os.environ.copy()

    env = os.environ.copy()
    mint_arg = ["--mints", ",".join(mints)] if mints else []

    tsnode_local = js_root / "node_modules" / ".bin" / ("ts-node.cmd" if os.name == "nt" else "ts-node")
    if tsnode_local.exists():
        return (
            [str(tsnode_local), "--transpile-only", str(script), "--owner", owner_pubkey, *mint_arg],
            js_root,
            env,
        )

    npx = which("npx.cmd") if os.name == "nt" else which("npx")
    if npx:
        return (
            [npx, "--yes", "ts-node", "--transpile-only", str(script), "--owner", owner_pubkey, *mint_arg],
            js_root,
            env,
        )

    node = which("node") or ("node" if os.name != "nt" else r"C:\\Program Files\\nodejs\\node.exe")
    if node:
        return (
            [node, "-r", "ts-node/register/transpile-only", str(script), "--owner", owner_pubkey, *mint_arg],
            js_root,
            env,
        )

    print("❌ Could not locate ts-node, npx, or node executables.")
    print("   Checked:", tsnode_local, "and PATH for npx/node.")
    return None, js_root, env


def run_ts_valuation(owner_pubkey: str, mints: list[str] | None = None) -> int:
    """
    Run the TS helper to value Raydium CL positions for this owner.
    Prefers local ts-node (node_modules/.bin) to avoid PATH issues.
    Falls back to npx, then to node -r ts-node/register.
    Always prints the actual command and returns a real exit code.
    """
    import subprocess

    mints = mints or []
    cmd, js_root, env = _ts_valuation_command(owner_pubkey, mints)
    if not cmd:
        return 1

    print("   • Exec:", " ".join(str(c) for c in cmd))
    try:
        proc = subprocess.run(cmd, cwd=str(js_root), env=env)
        return int(proc.returncode or 0)
    except FileNotFoundError as e:
        print("   • File not found:", e)
        return 127
    except Exception as e:
        print("   • Exec failed:", e)
        return 1


def _run_ts_value_and_store(owner: str, mints: list[str]) -> int:
    import subprocess

    cmd, js_root, env = _ts_valuation_command(owner, mints)
    if not cmd:
        return 1

    print("   • Exec:", " ".join(str(c) for c in cmd))
    payload: Optional[Dict[str, Any]] = None
    try:
        with subprocess.Popen(
            cmd,
            cwd=str(js_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        ) as proc:
            assert proc.stdout is not None
            for raw in proc.stdout:
                line = raw.rstrip("\n")
                print(line)
                stripped = line.strip()
                if stripped.startswith("{") and stripped.endswith("}"):
                    try:
                        payload = json.loads(stripped)
                    except Exception:
                        continue
            proc.wait()
            rc = int(proc.returncode or 0)
    except FileNotFoundError as e:
        print("   • File not found:", e)
        return 127
    except Exception as e:
        print("   • Exec failed:", e)
        return 1

    if payload and isinstance(payload.get("rows") or payload.get("details"), list):
        try:
            dl = DataLocker.get_instance()
            owner_pk = owner
            if getattr(dl, "system", None) and hasattr(dl.system, "set_var"):
                dl.system.set_var("raydium_positions", payload.get("rows") or [])
            saved = dl.raydium.upsert_from_ts_payload(owner_pk, payload)
            print(f"   • Upserted {saved} CLMM NFT row(s) → DB.raydium_nfts (+history)")
        except Exception as e:
            print(f"   • Note: failed to persist to DataLocker: {e}")

    return rc


def run_ts_prices(mints: list[str] | None = None) -> int:
    """
    Run the TS prices helper for a set of mints (uses Jupiter price API).
    Prefers the local ts-node shim to avoid PATH/npx issues.
    """
    from pathlib import Path
    from shutil import which
    import subprocess, os

    mints = mints or []
    js_root = Path(__file__).resolve().parent.parent / "ts"
    script = js_root / "fetch_prices.ts"
    if not script.exists():
        print("❌ TS prices script not found:", script)
        print("   Ensure files are under backend/core/raydium_core/ts and run npm i")
        return 1

    env = os.environ.copy()
    mint_arg = ["--mints", ",".join(mints)] if mints else []

    def _run(cmd: list[str]) -> int:
        print("   • Exec:", " ".join(str(c) for c in cmd))
        try:
            p = subprocess.run(cmd, cwd=str(js_root), env=env)
            return int(p.returncode)
        except FileNotFoundError as e:
            print("   • File not found:", e)
            return 127
        except Exception as e:
            print("   • Exec failed:", e)
            return 1

    tsnode_local = js_root / "node_modules" / ".bin" / ("ts-node.cmd" if os.name == "nt" else "ts-node")
    if tsnode_local.exists():
        return _run([str(tsnode_local), "--transpile-only", str(script), *mint_arg])

    npx = which("npx.cmd") if os.name == "nt" else which("npx")
    if npx:
        return _run([npx, "--yes", "ts-node", "--transpile-only", str(script), *mint_arg])

    node = which("node") or ("node" if os.name != "nt" else r"C:\\Program Files\\nodejs\\node.exe")
    if node:
        return _run([node, "-r", "ts-node/register/transpile-only", str(script), *mint_arg])

    print("❌ Could not locate ts-node, npx, or node executables.")
    return 1





# ---------- Menu ----------

def main():
    rpc = _resolve_rpc_url()
    banner("🌊 Raydium Core Console", f"RPC: {rpc}")

    cl = SolClient(rpc)
    while True:
        print("❯ 1) 🔑  Show loaded wallet")
        print("  2) 🖼️  List NFT-like tokens (dec=0, amt>=1; Token + Token-2022 if available)")
        print("  3) 💎  List Raydium NFTs (COMING SOON: allowlist filter)")
        print("  4) 💰 Value Raydium CL positions (TS helper)")
        print("  5) 💵 Value CLMM NFTs (SDK + Jupiter)")
        print("  0) 🚪  Exit")
        choice = ask("\nPick", "1")
        if choice == "1":
            owner = show_wallet(cl)
            pause()
        elif choice == "2":
            owner = show_wallet(cl)
            print("\n🕵️  Scanning token accounts for NFT pattern…")
            nftish = list_suspected_nfts(cl, owner, verbose=False)
            print(f"\n   Found {len(nftish)} candidates\n")
            print_nfts(nftish)
            pause()
        elif choice == "3":
            print("\n💎 Raydium filtered view will use a creator/collection allowlist next pass.")
            print("   (We’ll wire a JSON allowlist and metadata PDA checks.)")
            pause()
        elif choice == "4":
            owner = show_wallet(cl)
            print("\n📈 Valuing Raydium CL positions via SDK…")
            nftish = list_suspected_nfts(cl, owner, verbose=False)
            mints = [m for (m, _ta, _strong) in nftish]
            print("   • Mints →", ",".join(mints) if mints else "(none)")
            rc = run_ts_valuation(str(owner), mints)
            print("\n(Exit code:", rc, ")")
            pause()
        elif choice == "5":
            owner = show_wallet(cl)
            print("\n💵 Valuing CLMM NFTs via services…")
            # 1) discover (safe if none found)
            found = scan_owner_nfts(str(owner))
            # 2) value (uses sdk+jupiter; persists to DB)
            saved = value_owner_nfts(str(owner))
            # 3) populate panel fallback var from DB for immediate view
            try:
                dl = DataLocker.get_instance()
                rows = dl.raydium.get_by_owner(str(owner))
                if getattr(dl, "system", None) and hasattr(dl.system, "set_var"):
                    dl.system.set_var("raydium_positions", rows)
            except Exception:
                pass
            print(f"   • scanned={found}, saved={saved}")
            pause()
        elif choice == "0":
            print("\n👋 Done.")
            return
        else:
            print("   Unknown option.")


if __name__ == "__main__":
    main()
