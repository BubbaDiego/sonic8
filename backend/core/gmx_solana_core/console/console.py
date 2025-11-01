"""
GMX-Solana Core Console (Phase S-2)

Commands:
  ping
  config
  smoke
  markets
  positions --wallet <pubkey>
"""
import argparse
import os
from pathlib import Path
from ..config_loader import load_solana_config, pretty
from ..clients.solana_rpc_client import SolanaRpcClient
from ..services.market_service import MarketService
from ..services.position_source_solana import SolanaPositionSource

PKG_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CFG = PKG_ROOT / "config" / "solana.yaml"

def _load_cfg(args):
    cfg_path = Path(args.config) if getattr(args, "config", None) else DEFAULT_CFG
    cfg = load_solana_config(str(cfg_path))
    return cfg

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

def cmd_markets(args):
    cfg = _load_cfg(args)
    rpc = _mk_rpc(cfg)
    ms = MarketService(rpc_client=rpc, idl_loader=None)
    # Program ID comes from config.solana.programs.store or ENV:GMSOL_STORE
    programs = cfg.get("programs") or {}
    store_pid = programs.get("store") or os.environ.get("GMSOL_STORE")
    if not store_pid:
        print("⚠️  Missing program id for GMX-Solana Store. Set config.solana.programs.store or $env:GMSOL_STORE")
        return 2
    info = ms.list_markets_basic(store_pid)
    print(pretty(info))
    return 0

def cmd_positions(args):
    cfg = _load_cfg(args)
    rpc = _mk_rpc(cfg)
    src = SolanaPositionSource(rpc_client=rpc)
    # In S-2.1 we’ll add real account decoding via IDL and proper memcmp filters.
    print("ℹ️  positions reading requires IDL offsets; wiring in Phase S-2.1.")
    print("   Provided wallet:", args.wallet)
    return 0

def build_parser():
    p = argparse.ArgumentParser(prog="gmx_solana_console", description="GMX-Solana Console")
    p.add_argument("--config", help="Path to solana.yaml (defaults to package config)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("ping")
    s.set_defaults(func=cmd_ping)

    s = sub.add_parser("config")
    s.set_defaults(func=cmd_config)

    s = sub.add_parser("smoke")
    s.set_defaults(func=cmd_smoke)

    s = sub.add_parser("markets", help="list basic market info via Store program")
    s.set_defaults(func=cmd_markets)

    s = sub.add_parser("positions", help="list wallet positions (S-2.1 will decode)")
    s.add_argument("--wallet", required=True, help="wallet public key")
    s.set_defaults(func=cmd_positions)
    return p

def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
