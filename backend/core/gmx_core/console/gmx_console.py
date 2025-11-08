from __future__ import annotations

import argparse
import json

# use absolute import so both `-m` and direct-path runs work cleanly
from backend.core.gmx_core.services import gmx_service


def main() -> None:
    ap = argparse.ArgumentParser(description="GMX Console (base)")
    ap.add_argument("--cluster", default="mainnet", choices=["mainnet", "devnet"])
    ap.add_argument("--signer", default=None, help="Path to signer.txt (12-word mnemonic)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("health")
    sub.add_parser("markets")
    sub.add_parser("positions")

    args = ap.parse_args()
    signer = args.signer or None

    if args.cmd == "health":
        out = gmx_service.get_health(cluster=args.cluster, signer_path=signer)
    elif args.cmd == "markets":
        out = {"markets": gmx_service.get_markets(cluster=args.cluster, signer_path=signer)}
    elif args.cmd == "positions":
        out = {"positions": gmx_service.get_positions(cluster=args.cluster, signer_path=signer)}
    else:
        out = {"ok": False, "err": "unknown command"}

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
