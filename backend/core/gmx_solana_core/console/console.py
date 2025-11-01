"""
GMX-Solana Core Console (Phase S-2.1)

Commands:
  ping
  config
  smoke
  markets [--store <pid>]
  positions --wallet <pubkey> [--store <pid>] [--owner-offset <int>]
"""
import argparse
import os
from pathlib import Path
from ..config_loader import load_solana_config, pretty
from ..clients.solana_rpc_client import SolanaRpcClient, RpcError
from ..services.market_service import MarketService
from ..services.position_source_solana import SolanaPositionSource

PKG_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CFG = PKG_ROOT / "config" / "solana.yaml"

def _load_cfg(args):
    cfg_path = Path(args.config) if getattr(args, "config", None) else DEFAULT_CFG
    cfg = load_solana_config(str(cfg_path))
    return cfg

def _ensure_base58(s: str, label: str):
    # cheap base58 validation (length + charset) to fail fast with friendly error
    import re
    if not isinstance(s, str) or len(s) < 32:
        raise ValueError(f"{label} looks invalid (too short).")
    if re.search(r"[^1-9A-HJ-NP-Za-km-z]", s):
        raise ValueError(f"{label} must be base58 (no 0,O,I,l or symbols).")

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

def _mk_rpc(cfg):
    rpc_http = cfg.get("rpc_http")
    return SolanaRpcClient(rpc_http)

def _resolve_store(args, cfg):
    # priority: flag -> config -> env
    if getattr(args, "store", None):
        return args.store
    programs = cfg.get("programs") or {}
    pid = programs.get("store") or os.environ.get("GMSOL_STORE")
    return pid

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
    if args.owner_offset is None:
        print("⚠️  Missing --owner-offset <N>. Pass the byte offset of owner pubkey within the position account.")
        return 2
    try:
        _ensure_base58(store_pid, "Store program id")
        _ensure_base58(args.wallet, "Wallet pubkey")
        info = src.list_open_positions_basic(store_program=store_pid, wallet_b58=args.wallet, owner_offset=args.owner_offset)
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
    s.add_argument("--wallet", required=True, help="wallet public key (base58)")
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
