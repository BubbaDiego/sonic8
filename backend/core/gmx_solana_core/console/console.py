"""
GMX-Solana Core Console (Phase S-2.1, signer-aware)

Commands:
  ping
  config
  smoke
  markets [--store <pid>]
  positions [--wallet <pubkey> | --wallet-from-signer [--signer-file <path>]]
            [--store <pid>] [--owner-offset <int>]

- --wallet-from-signer: attempts to import backend.services.signer_loader and
  pull a wallet pubkey or mnemonic from signer.txt at repo root (or --signer-file).
  If only a mnemonic is found and we can't derive pubkey without extra deps,
  we print a clear hint.
"""
import argparse
import os
from pathlib import Path
from typing import Optional

from ..config_loader import load_solana_config, pretty
from ..clients.solana_rpc_client import SolanaRpcClient, RpcError
from ..services.market_service import MarketService
from ..services.position_source_solana import SolanaPositionSource

PKG_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CFG = PKG_ROOT / "config" / "solana.yaml"

# --------- helpers ---------
def _load_cfg(args):
    cfg_path = Path(args.config) if getattr(args, "config", None) else DEFAULT_CFG
    cfg = load_solana_config(str(cfg_path))
    return cfg

def _ensure_base58(s: str, label: str):
    import re
    if not isinstance(s, str) or len(s) < 32:
        raise ValueError(f"{label} looks invalid (too short).")
    if re.search(r"[^1-9A-HJ-NP-Za-km-z]", s):
        raise ValueError(f"{label} must be base58 (no 0,O,I,l or symbols).")

def _mk_rpc(cfg):
    rpc_http = cfg.get("rpc_http")
    return SolanaRpcClient(rpc_http)

def _resolve_store(args, cfg) -> Optional[str]:
    # priority: --store → config.solana.programs.store → $GMSOL_STORE
    if getattr(args, "store", None):
        return args.store
    programs = (cfg.get("programs") or {})
    pid = programs.get("store") or os.environ.get("GMSOL_STORE")
    return pid

def _resolve_signer_file(args) -> Path:
    # default to repo root signer.txt if not provided
    if getattr(args, "signer_file", None):
        return Path(args.signer_file)
    # try CWD/signers: project root typical
    cwd = Path.cwd()
    return cwd / "signer.txt"

def _wallet_from_signer_file(signer_path: Path) -> Optional[str]:
    """
    Try to load wallet pubkey using existing code in backend.services.signer_loader,
    falling back to simple heuristics. We do NOT add extra deps here.
    """
    # Try to import your project's loader
    try:
        from importlib import import_module
        sl = import_module("backend.services.signer_loader")

        # Try a few likely entrypoints in order of specificity
        for attr in ("load_wallet_pubkey", "get_wallet_pubkey", "wallet_pubkey", "load_signer_pubkey"):
            if hasattr(sl, attr):
                fn = getattr(sl, attr)
                try:
                    key = fn(str(signer_path))
                    if isinstance(key, str):
                        return key
                except Exception:
                    pass

        # Fallback: try a generic "load_signer" that returns an object with .public_key
        for attr in ("load_signer", "get_signer", "load_mnemonic"):
            if hasattr(sl, attr):
                fn = getattr(sl, attr)
                try:
                    obj = fn(str(signer_path))
                    # if it has .public_key attribute, stringify it
                    if hasattr(obj, "public_key"):
                        pk = getattr(obj, "public_key")
                        return str(pk)
                    # if it returned mnemonic, we would need extra deps to derive
                    if isinstance(obj, str) and len(obj.split()) >= 12:
                        print("ℹ️  Found mnemonic in signer.txt via signer_loader, but pubkey derivation requires extra libs.")
                        print("   Suggest installing a helper (e.g., `pip install bip-utils`), or expose a `load_wallet_pubkey()` in signer_loader.")
                        return None
                except Exception:
                    pass
    except Exception:
        # ignore import errors; try trivial fallback below
        pass

    # Last resort: read file and see if it already contains a pubkey-looking string
    if signer_path.exists():
        txt = signer_path.read_text(encoding="utf-8").strip()
        parts = txt.split()
        if len(parts) == 1:
            # single token; maybe already a base58 pubkey?
            try:
                _ensure_base58(parts[0], "Wallet pubkey in signer.txt")
                return parts[0]
            except Exception:
                pass

    return None

# --------- commands ---------
def cmd_ping(args):
    print("OK: gmx_solana_core console is alive.")

def cmd_config(args):
    cfg = _load_cfg(args)
    print(pretty(cfg))

def cmd_smoke(args):
    problems = 0
    if not DEFAULT_CFG.exists():
        print(f"missing config file: {DEFAULT_CFG}")
        problems += 1
    else:
        print("config file: ok ✅")
    try:
        _ = load_solana_config(str(DEFAULT_CFG))
        print("config load + ENV resolve: ok ✅")
    except Exception as e:
        print("config error:", e)
        problems += 1
    print("result:", "PASS ✅" if problems == 0 else "FAIL ❌")
    return problems

def cmd_markets(args):
    cfg = _load_cfg(args)
    rpc = _mk_rpc(cfg)
    ms = MarketService(rpc_client=rpc, idl_loader=None)
    store_pid = _resolve_store(args, cfg)
    if not store_pid:
        print("⚠️  Missing Store program id. Pass --store <PROGRAM_ID>, set config.solana.programs.store, or $env:GMSOL_STORE")
        return 2
    try:
        _ensure_base58(store_pid, "Store program id")
        info = ms.list_markets_basic(store_pid)
        print(pretty(info))
        return 0
    except (ValueError, RpcError) as e:
        print(f"error: {e}")
        return 2

def cmd_positions(args):
    cfg = _load_cfg(args)
    rpc = _mk_rpc(cfg)
    src = SolanaPositionSource(rpc_client=rpc)
    store_pid = _resolve_store(args, cfg)
    if not store_pid:
        print("⚠️  Missing Store program id. Pass --store <PROGRAM_ID>, set config.solana.programs.store, or $env:GMSOL_STORE")
        return 2

    if args.wallet_from_signer:
        signer_path = _resolve_signer_file(args)
        wallet = _wallet_from_signer_file(signer_path)
        if not wallet:
            print(f"⚠️  Could not derive wallet from signer file: {signer_path}")
            print("   Please expose a pubkey function in backend.services.signer_loader, or pass --wallet <pubkey> directly.")
            return 2
        args.wallet = wallet

    if not args.wallet:
        print("⚠️  Missing wallet. Pass --wallet <pubkey> or --wallet-from-signer [--signer-file <path>].")
        return 2

    if args.owner_offset is None:
        print("⚠️  Missing --owner-offset <N>. Pass the byte offset of owner pubkey within the position account.")
        return 2

    try:
        _ensure_base58(store_pid, "Store program id")
        _ensure_base58(args.wallet, "Wallet pubkey")
        info = src.list_open_positions_basic(
            store_program=store_pid,
            wallet_b58=args.wallet,
            owner_offset=args.owner_offset,
        )
        print(pretty(info))
        return 0
    except (ValueError, RpcError) as e:
        print(f"error: {e}")
        return 2

def build_parser():
    p = argparse.ArgumentParser(prog="gmx_solana_console", description="GMX-Solana Console")
    p.add_argument("--config", help="Path to solana.yaml (defaults to package config)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("ping");    s.set_defaults(func=cmd_ping)
    s = sub.add_parser("config");  s.set_defaults(func=cmd_config)
    s = sub.add_parser("smoke");   s.set_defaults(func=cmd_smoke)

    s = sub.add_parser("markets", help="enumerate Store accounts (sanity)")
    s.add_argument("--store", help="GMX-Solana Store program id (overrides env/config)")
    s.set_defaults(func=cmd_markets)

    s = sub.add_parser("positions", help="list wallet positions via memcmp (S-2.1)")
    s.add_argument("--wallet", help="wallet public key (base58)")
    s.add_argument("--wallet-from-signer", action="store_true", help="derive wallet pubkey from signer.txt via signer_loader")
    s.add_argument("--signer-file", help="path to signer.txt (default: ./signer.txt)")
    s.add_argument("--store", help="GMX-Solana Store program id (overrides env/config)")
    s.add_argument("--owner-offset", type=int, required=False)
    s.set_defaults(func=cmd_positions)

    return p

def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
