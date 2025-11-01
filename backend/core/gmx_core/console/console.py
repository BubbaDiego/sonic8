import argparse
import os
import sys

from ..config_loader import load_config, get_chain_cfg, pretty
from ..clients.gmx_rest_client import GmxRestClient
from ..clients.subsquid_client import SubsquidClient
from ..services.position_source import GMXPositionSource
from ..dl.positions_writer import write_positions

def _load_chain_clients(cfg_path: str, chain_key: str):
    cfg = load_config(cfg_path)
    chain = get_chain_cfg(cfg, chain_key)

    rest_hosts = chain.get("rest_hosts") or []
    subsquid_url = chain.get("subsquid_url")
    if not subsquid_url:
        raise RuntimeError("subsquid_url is required for Phase 2 (read path).")

    rest = GmxRestClient(rest_hosts)
    squid = SubsquidClient(subsquid_url)

    return chain, rest, squid

def cmd_ping(args):
    print("OK: gmx_core console is alive.")

def cmd_config_show(args):
    from ..config_loader import pretty
    cfg = load_config(args.config)
    print(pretty(cfg))

def cmd_markets(args):
    chain, rest, squid = _load_chain_clients(args.config, args.chain)
    # Simple call to verify REST connectivity
    info = rest.get_markets_info()
    print(pretty(info) if args.raw else f"OK: markets/info fetched for {args.chain} ({len((info or {}).get('markets', [])) or 'n/a'} items)")

def cmd_positions(args):
    chain, rest, squid = _load_chain_clients(args.config, args.chain)
    src = GMXPositionSource(args.chain, rest, squid)
    pos = src.list_open_positions(args.wallet, limit=args.limit)
    if args.raw:
        from ..config_loader import pretty
        print(pretty([p.__dict__ for p in pos]))
        return
    norm = src.normalize(pos) if args.normalize else None
    if norm:
        from ..config_loader import pretty
        print(pretty([p.__dict__ for p in norm]))
    else:
        print(f"Found {len(pos)} open positions for {args.wallet} on {args.chain} (use --normalize to map to DL schema)")

def cmd_write_positions(args):
    chain, rest, squid = _load_chain_clients(args.config, args.chain)
    src = GMXPositionSource(args.chain, rest, squid)
    pos = src.list_open_positions(args.wallet, limit=args.limit)
    norm = src.normalize(pos)
    # If your DL needs a handle, pass via code here. We default to module discovery.
    write_positions(dl=None, positions=norm, dry_run=args.dry_run)

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gmx_core_console", description="GMX Core Console (Phase 2)")
    p.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "..", "config", "gmx_chains.yaml"))
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("ping")
    s.set_defaults(func=cmd_ping)

    s = sub.add_parser("config")
    s.add_argument("--show", action="store_true")
    s.set_defaults(func=cmd_config_show)

    s = sub.add_parser("markets")
    s.add_argument("--chain", required=True, choices=["arbitrum", "avalanche"])
    s.add_argument("--raw", action="store_true")
    s.set_defaults(func=cmd_markets)

    s = sub.add_parser("positions")
    s.add_argument("--chain", required=True, choices=["arbitrum", "avalanche"])
    s.add_argument("--wallet", required=True)
    s.add_argument("--limit", type=int, default=1000)
    s.add_argument("--raw", action="store_true", help="print raw Subsquid rows")
    s.add_argument("--normalize", action="store_true", help="map to NormalizedPosition")
    s.set_defaults(func=cmd_positions)

    s = sub.add_parser("write-positions")
    s.add_argument("--chain", required=True, choices=["arbitrum", "avalanche"])
    s.add_argument("--wallet", required=True)
    s.add_argument("--limit", type=int, default=1000)
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_write_positions)

    return p

def main(argv=None):
    argv = argv or sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "config" and args.show:
        return cmd_config_show(args)
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(2)
    return args.func(args)

if __name__ == "__main__":
    main()
