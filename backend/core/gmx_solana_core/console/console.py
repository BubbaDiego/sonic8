"""
GMX-Solana Core Console (Phase S-1)

Commands:
  ping
  config --show
  smoke

This console loads only the Solana subtree of the config to avoid touching
EVM envs for other packages.
"""
import argparse
import os
from pathlib import Path
from ..config_loader import load_solana_config, pretty

PKG_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CFG = PKG_ROOT / "config" / "solana.yaml"

def cmd_ping(args):
    print("OK: gmx_solana_core console is alive.")

def cmd_config_show(args):
    cfg_path = Path(args.config) if args.config else DEFAULT_CFG
    print(f"config path: {cfg_path}")
    cfg = load_solana_config(str(cfg_path))
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

def build_parser():
    p = argparse.ArgumentParser(prog="gmx_solana_console", description="GMX-Solana Console")
    p.add_argument("--config", help="Path to solana.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("ping")
    s.set_defaults(func=cmd_ping)

    s = sub.add_parser("config")
    s.set_defaults(func=cmd_config_show)

    s = sub.add_parser("smoke")
    s.set_defaults(func=cmd_smoke)

    return p

def main(argv=None):
    argv = argv or None
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
