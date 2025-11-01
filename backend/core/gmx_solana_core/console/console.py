"""
GMX-Solana Core Console (Phase S-2.1+) – signer-aware + rpc-ping + light markets
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

def _load_cfg(args):
    cfg_path = Path(args.config) if getattr(args, "config", None) else DEFAULT_CFG
    return load_solana_config(str(cfg_path))

def _ensure_base58(s: str, label: str):
    import re
    if not isinstance(s, str) or len(s) < 32:
        raise ValueError(f"{label} looks invalid (too short).")
    if re.search(r"[^1-9A-HJ-NP-Za-km-z]", s):
        raise ValueError(f"{label} must be base58 (no 0,O,I,l or symbols).")

def _mk_rpc(cfg):
    return SolanaRpcClient(cfg.get("rpc_http"))

def _resolve_store(args, cfg) -> Optional[str]:
    if getattr(args, "store", None):
        return args.store
    programs = (cfg.get("programs") or {})
    return programs.get("store") or os.environ.get("GMSOL_STORE")

def _resolve_signer_file(args) -> Path:
    if getattr(args, "signer_file", None):
        return Path(args.signer_file)
    p = Path.cwd() / "signer.txt"
    if p.exists(): return p
    return Path.cwd() / "signer"

def _wallet_from_signer_file(signer_path: Path) -> Optional[str]:
    try:
        from importlib import import_module
        sl = import_module("backend.services.signer_loader")
        for attr in ("load_wallet_pubkey","get_wallet_pubkey","wallet_pubkey","load_signer_pubkey"):
            if hasattr(sl, attr):
                try:
                    val = getattr(sl, attr)(str(signer_path))
                    if isinstance(val, str): return val
                except Exception: pass
        for attr in ("load_signer","get_signer","load_mnemonic"):
            if hasattr(sl, attr):
                try:
                    obj = getattr(sl, attr)(str(signer_path))
                    if hasattr(obj, "public_key"): return str(getattr(obj,"public_key"))
                    if isinstance(obj, str) and len(obj.split()) >= 12:
                        print("ℹ️  Found mnemonic; expose a pubkey function in signer_loader or pass --wallet directly.")
                        return None
                except Exception: pass
    except Exception: pass
    if signer_path.exists():
        txt = signer_path.read_text(encoding="utf-8").strip().split()
        if len(txt)==1:
            try:
                _ensure_base58(txt[0], "Wallet pubkey in signer file"); return txt[0]
            except Exception: pass
    return None

# ---- commands
def cmd_ping(args): print("OK: gmx_solana_core console is alive.")

def cmd_config(args): print(pretty(_load_cfg(args)))

def cmd_smoke(args):
    ok, msg = True, []
    if not DEFAULT_CFG.exists(): ok=False; msg.append(f"missing config file: {DEFAULT_CFG}")
    else: msg.append("config file: ok ✅")
    try: _=load_solana_config(str(DEFAULT_CFG)); msg.append("config load + ENV resolve: ok ✅")
    except Exception as e: ok=False; msg.append(f"config error: {e}")
    print("\n".join(msg)); print("result:", "PASS ✅" if ok else "FAIL ❌"); return 0 if ok else 2

def cmd_rpc_ping(args):
    cfg = _load_cfg(args); rpc = _mk_rpc(cfg)
    try:
        health = rpc.get_health()
    except RpcError as e:
        print("getHealth error:", e); health = "error"
    try:
        slot = rpc.get_slot()
    except RpcError as e:
        print("getSlot error:", e); slot = -1
    print(pretty({"health": health, "slot": slot})); return 0

def cmd_markets(args):
    cfg = _load_cfg(args); rpc = _mk_rpc(cfg); ms = MarketService(rpc_client=rpc)
    store_pid = _resolve_store(args, cfg)
    if not store_pid:
        print("⚠️  Missing Store program id. Use --store <PROGRAM_ID>, config.solana.programs.store, or $GMSOL_STORE")
        return 2
    try:
        _ensure_base58(store_pid, "Store program id")
        info = ms.list_markets_basic(store_pid, limit=args.limit, page=args.page)
        print(pretty(info)); return 0
    except (ValueError, RpcError) as e:
        print(f"error: {e}"); return 2

def cmd_positions(args):
    cfg = _load_cfg(args); rpc = _mk_rpc(cfg); src = SolanaPositionSource(rpc_client=rpc)
    store_pid = _resolve_store(args, cfg)
    if not store_pid:
        print("⚠️  Missing Store program id. Use --store <PROGRAM_ID>, config.solana.programs.store, or $GMSOL_STORE")
        return 2
    if args.wallet_from_signer:
        signer_path = _resolve_signer_file(args)
        w = _wallet_from_signer_file(signer_path)
        if not w:
            print(f"⚠️  Could not derive wallet from signer file: {signer_path}")
            return 2
        args.wallet = w
    if not args.wallet:
        print("⚠️  Missing wallet. Pass --wallet <pubkey> or --wallet-from-signer [--signer-file <path>].")
        return 2
    if args.owner_offset is None:
        print("⚠️  Missing --owner-offset <N>."); return 2
    try:
        _ensure_base58(store_pid, "Store program id")
        _ensure_base58(args.wallet, "Wallet pubkey")
        info = src.list_open_positions_basic(store_program=store_pid, wallet_b58=args.wallet, owner_offset=args.owner_offset)
        print(pretty(info)); return 0
    except (ValueError, RpcError) as e:
        print(f"error: {e}"); return 2

def build_parser():
    p = argparse.ArgumentParser(prog="gmx_solana_console", description="GMX-Solana Console")
    p.add_argument("--config", help="Path to solana.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping").set_defaults(func=cmd_ping)
    sub.add_parser("config").set_defaults(func=cmd_config)
    sub.add_parser("smoke").set_defaults(func=cmd_smoke)
    sub.add_parser("rpc-ping").set_defaults(func=cmd_rpc_ping)

    s = sub.add_parser("markets", help="enumerate Store accounts (paged)")
    s.add_argument("--store", help="GMX-Solana Store program id (overrides env/config)")
    s.add_argument("--limit", type=int, default=100)
    s.add_argument("--page", type=int, default=1)
    s.set_defaults(func=cmd_markets)

    s = sub.add_parser("positions", help="list wallet positions via memcmp (S-2.1)")
    s.add_argument("--wallet", help="wallet public key (base58)")
    s.add_argument("--wallet-from-signer", action="store_true")
    s.add_argument("--signer-file", help="path to signer.txt/signer")
    s.add_argument("--store", help="GMX-Solana Store program id (overrides env/config)")
    s.add_argument("--owner-offset", type=int)
    s.set_defaults(func=cmd_positions)
    return p

def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
