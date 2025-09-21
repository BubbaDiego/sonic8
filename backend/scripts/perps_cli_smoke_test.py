#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jupiter Perps — CLI Smoke Tester (Python)

Zero-arg mode (just run this file):
  - Action: open (increase) market position
  - Market: SOL
  - Side:   long
  - Size:   20 USD
  - Collat: 12 (UI units; WSOL for long)
  - Guard:  --max-price 1000000 (wide; override via env)

Environment overrides (optional):
  SOLANA_RPC_URL            -> RPC endpoint (default: https://api.mainnet-beta.solana.com)
  JUP_PERPS_REPO_DIR        -> path to jupiter-perps-anchor-idl-parsing
  ANCHOR_WALLET / KEYPAIR   -> keypair path (JSON array, base58 file, or id.json)
  JUP_PERPS_LIVE=1          -> send tx (otherwise dry-run by default)
  JUP_PERPS_MAX_PRICE=NNN   -> override default max-price guardrail for LONG

Manual mode (explicit):
  python backend/scripts/perps_cli_smoke_test.py \
    --repo-dir "C:\\jupiter-perps-anchor-idl-parsing" \
    --rpc "https://api.mainnet-beta.solana.com" \
    --kp  "C:\\sonic5\\keys\\trader.json" \
    --market SOL --side long \
    open --size-usd 5 --collat 0.02
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import List, Tuple, Optional

# ──────────────────────────────────────────── Pretty logging ────────────────────────────────────────────
def bar(title: str, emoji: str = "🧭") -> None:
    line = "─" * max(12, 72 - len(title))
    print(f"\n{line} {emoji}  {title}  {emoji} {line}")

def info(msg: str, emoji: str = "ℹ️") -> None:
    print(f"{emoji}  {msg}")

def ok(msg: str) -> None:
    print(f"✅  {msg}")

def warn(msg: str) -> None:
    print(f"⚠️  {msg}")

def fail(msg: str, code: int = 1) -> None:
    print(f"🛑  {msg}")
    sys.exit(code)

def kv(label: str, value: str) -> None:
    print(f"  • {label.ljust(22)} = {value}")

# ───────────────────────────────────────────── Helpers ─────────────────────────────────────────────
B58_RE = r"[1-9A-HJ-NP-Za-km-z]{32,64}"

def find_tx_sig(text: str) -> Optional[str]:
    m = re.search(r"Tx sent:\s*([A-Za-z0-9]+)", text or "")
    return m.group(1) if m else None

def find_pos_request(text: str) -> Optional[str]:
    m = re.search(r"PositionRequest\s*=\s*(" + B58_RE + r")", text or "")
    return m.group(1) if m else None

def run_cmd(cmd: List[str], cwd: Path, timeout: int = 300, env: Optional[dict] = None) -> Tuple[int, str, str]:
    """
    Robust, Windows-safe command runner.
    - Always captures bytes and decodes to UTF-8 (replace invalid) to avoid UnicodeDecodeError.
    - Uses shell=True on Windows so *.cmd shims (npm/npx) resolve.
    """
    if os.name == "nt":
        cmd_str = " ".join([f'"{c}"' if (" " in str(c)) else str(c) for c in cmd])
        proc = subprocess.run(
            cmd_str, cwd=str(cwd),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=False, timeout=timeout, shell=True, env=env
        )
    else:
        proc = subprocess.run(
            cmd, cwd=str(cwd),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=False, timeout=timeout, shell=False, env=env
        )
    out = (proc.stdout or b"").decode("utf-8", errors="replace")
    err = (proc.stderr or b"").decode("utf-8", errors="replace")
    return proc.returncode, out, err

def ensure_npm_available() -> None:
    for tool in ("npm", "npx"):
        if shutil.which(tool) is None:
            fail(f"{tool} was not found on PATH. Install Node/npm or open a shell where {tool} is available.")

# ───────────────────────────────────────────── signer.txt support ─────────────────────────────────────────────
def read_signer_txt(roots: List[Path]) -> Optional[dict]:
    """Parse signer.txt lines like: address=..., base58=..., mnemonic=..., passphrase=..."""
    for root in roots:
        p = root / "signer.txt"
        if p.exists():
            try:
                data = {}
                for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        data[k.strip().lower()] = v.strip().strip('"').strip("'")
                if data:
                    return data
            except Exception:
                pass
    return None

def materialize_kp_from_base58(base58_secret: str, dest_dir: Path) -> Path:
    """Create a small file containing ONLY the base58 secret; the TS loader accepts this."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / "kp_from_signer_base58.txt"
    out.write_text(base58_secret.strip() + "\n", encoding="utf-8")
    warn(f"Using signer.txt base58 → {out} (ensure this path is protected / .gitignored)")
    return out

# ──────────────────────────────────────────── repo/keypair helpers ────────────────────────────────────────────
def guess_repo_dir() -> Path:
    env = os.getenv("JUP_PERPS_REPO_DIR")
    if env:
        p = Path(env).expanduser()
        if p.exists():
            return p
    here = Path(__file__).resolve()
    sonic_root = here.parents[2]  # .../sonic5
    cand = sonic_root / "jupiter-perps-anchor-idl-parsing"
    if cand.exists():
        return cand
    for c in [
        Path("C:/sonic5/jupiter-perps-anchor-idl-parsing"),
        Path.home() / "jupiter-perps-anchor-idl-parsing",
    ]:
        if c.exists():
            return c
    return cand

def guess_keypair_path() -> Optional[str]:
    for env in ("KEYPAIR", "ANCHOR_WALLET", "SOLANA_KEYPAIR"):
        v = os.getenv(env)
        if v and Path(v).expanduser().exists():
            return str(Path(v).expanduser())
    here = Path(__file__).resolve()
    sonic_root = here.parents[2]  # .../sonic5
    signer = read_signer_txt([sonic_root, Path.cwd()])
    if signer and "base58" in signer and signer["base58"]:
        keyfile = materialize_kp_from_base58(signer["base58"], sonic_root / "keys")
        return str(keyfile)
    for p in [
        sonic_root / "keys" / "trader.json",
        Path.home() / ".config" / "solana" / "id.json",
    ]:
        if p.exists():
            return str(p)
    return None

def load_package_json(repo_dir: Path) -> dict:
    pkg = repo_dir / "package.json"
    if not pkg.exists():
        fail(f"package.json not found in {repo_dir}")
    try:
        with pkg.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as e:
        fail(f"Failed reading package.json: {e}")
    return {}

def ensure_node_modules(repo_dir: Path) -> None:
    if (repo_dir / "node_modules").exists():
        return
    bar("Installing Node deps (npm install)", "📦")
    code, out, err = run_cmd(["npm", "install"], cwd=repo_dir, timeout=1800)
    if out.strip(): print(out)
    if err.strip(): print(err)
    if code != 0:
        fail("npm install failed")

def ensure_ts_node(repo_dir: Path) -> None:
    code, _, _ = run_cmd(["npx", "ts-node", "-v"], cwd=repo_dir, timeout=60)
    if code == 0:
        return
    bar("Installing ts-node + typescript (no-save)", "🧰")
    code, out, err = run_cmd(["npm", "i", "--no-save", "ts-node", "typescript"], cwd=repo_dir, timeout=600)
    if out.strip(): print(out)
    if err.strip(): print(err)
    if code != 0:
        fail("Failed to install ts-node/typescript")

def ensure_tsx(repo_dir: Path) -> None:
    code, _, _ = run_cmd(["npx", "tsx", "-v"], cwd=repo_dir, timeout=60)
    if code == 0:
        return
    bar("Installing tsx (no-save)", "🧰")
    code, out, err = run_cmd(["npm", "i", "--no-save", "tsx"], cwd=repo_dir, timeout=600)
    if out.strip(): print(out)
    if err.strip(): print(err)
    if code != 0:
        fail("Failed to install tsx")

def repo_sanity(repo_dir: Path, require_examples: bool = True) -> None:
    if not (repo_dir / "package.json").exists():
        fail(f"package.json not found in {repo_dir}")
    if require_examples:
        for rel in ("src/examples/perps_open_market.ts",
                    "src/examples/perps_add_collateral.ts",
                    "src/examples/perps_withdraw_collateral.ts"):
            p = repo_dir / rel
            if not p.exists():
                fail(f"Expected example missing: {p}")
    ensure_node_modules(repo_dir)

def common_args(ns: argparse.Namespace) -> List[str]:
    args = ["--rpc", ns.rpc, "--kp", ns.kp, "--market", ns.market, "--side", ns.side]
    # guardrail selection
    if ns.oracle_price is not None and ns.slip is not None:
        args += ["--oracle-price", f"{ns.oracle_price}", "--slip", f"{ns.slip}"]
    elif ns.max_price is not None:
        args += ["--max-price", f"{ns.max_price}"]
    elif ns.min_price is not None:
        args += ["--min-price", f"{ns.min_price}"]
    else:
        warn("No explicit guardrail provided; using per-action defaults.")
    if getattr(ns, "collat_mint", None):
        args += ["--collat-mint", ns.collat_mint]
    if getattr(ns, "desired_mint", None):
        args += ["--desired-mint", ns.desired_mint]
    if getattr(ns, "dry_run", False):
        args += ["--dry-run"]
    return args

# ───────────────────────────────────────────── Runners ─────────────────────────────────────────────
def try_runners(ns: argparse.Namespace, ts_path: str, extra: List[str]) -> Tuple[int, str, str]:
    """
    Try ESM-safe loader, then ts-node, then tsx.
    """
    repo = Path(ns.repo_dir)
    env = os.environ.copy()
    env["TS_NODE_TRANSPILE_ONLY"] = "1"

    # 1) node --loader ts-node/esm  (+ CJS-like extension resolution shim for .ts pathless imports)
    ensure_ts_node(repo)
    cmd1 = [
        "node",
        "--loader", "ts-node/esm",
        "--experimental-specifier-resolution=node",
        ts_path
    ] + common_args(ns) + extra
    bar("Runner: node --loader ts-node/esm", "🧪")
    code, out, err = run_cmd(cmd1, cwd=repo, timeout=ns.timeout, env=env)
    out = out or ""; err = err or ""
    if code == 0:
        return code, out, err
    # If it's not just the file-extension complaint, return to show real error quickly
    if "ERR_UNKNOWN_FILE_EXTENSION" not in (out + err) and "Cannot find module" not in (out + err):
        return code, out, err

    # 2) npx ts-node --transpile-only
    cmd2 = ["npx", "ts-node", "--transpile-only", ts_path] + common_args(ns) + extra
    bar("Runner: npx ts-node --transpile-only", "🧪")
    code, out, err = run_cmd(cmd2, cwd=repo, timeout=ns.timeout, env=env)
    out = out or ""; err = err or ""
    if code == 0:
        return code, out, err
    if "ERR_UNKNOWN_FILE_EXTENSION" not in (out + err) and "Cannot find module" not in (out + err):
        return code, out, err

    # 3) npx tsx (universal)
    ensure_tsx(repo)
    cmd3 = ["npx", "tsx", ts_path] + common_args(ns) + extra
    bar("Runner: npx tsx", "🧪")
    code, out, err = run_cmd(cmd3, cwd=repo, timeout=ns.timeout, env=env)
    return code, (out or ""), (err or "")

def run_ts_action(ns: argparse.Namespace, action: str, extra: List[str]) -> Tuple[Optional[str], Optional[str]]:
    mapping = {
        "open":      "src/examples/perps_open_market.ts",
        "add":       "src/examples/perps_add_collateral.ts",
        "withdraw":  "src/examples/perps_withdraw_collateral.ts",
    }
    ts_path = mapping.get(action)
    if not ts_path:
        fail(f"Unknown action {action}")

    bar(f"Execute: {action}", "📤")
    info("Command preview:", "🧾")
    print("   ", ts_path, *common_args(ns), *extra)

    code, out, err = try_runners(ns, ts_path, extra)
    print()
    if out.strip():
        bar("stdout", "🟢"); print(out)
    if err.strip():
        bar("stderr", "🟠"); print(err)
    if code != 0:
        fail(f"{action} failed with exit code {code}")

    tx = find_tx_sig(out) or find_tx_sig(err)
    pr = find_pos_request(out) or find_pos_request(err)
    if tx: ok(f"{action} → signature: {tx}")
    else:  warn(f"{action} → no signature found (dry-run or simulate?)")
    if pr: ok(f"{action} → position request: {pr}")
    else:  warn(f"{action} → no position request address detected")
    return tx, pr

# ───────────────────────────────────────────── CLI (manual) ─────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Smoke-test the Jupiter Perps TS CLI via Node/ts-node/tsx",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # where the TS repo lives
    p.add_argument("--repo-dir", help="Path to jupiter-perps-anchor-idl-parsing repo")
    # chain & wallet
    p.add_argument("--rpc", help="RPC URL (default from SOLANA_RPC_URL)")
    p.add_argument("--kp", help="Path to keypair (JSON array or base58 secret)")
    # market config
    p.add_argument("--market", choices=["SOL", "ETH", "BTC"], help="Market asset")
    p.add_argument("--side", choices=["long", "short"], help="Position side")
    p.add_argument("--collat-mint", help="Override collateral mint")
    p.add_argument("--desired-mint", help="Receiving mint for withdraw (defaults to collateral mint)")
    # guardrail options
    p.add_argument("--oracle-price", type=float, help="Oracle/mark price in USD")
    p.add_argument("--slip", type=float, help="Fractional slippage for guardrail (e.g., 0.02)")
    p.add_argument("--max-price", type=float, help="Explicit max price (LONG)")
    p.add_argument("--min-price", type=float, help="Explicit min price (SHORT)")
    # behavior
    p.add_argument("--dry-run", action="store_true", help="Force dry-run")
    p.add_argument("--timeout", type=int, default=300, help="Per-command timeout (seconds)")

    sub = p.add_subparsers(dest="action")

    open_p = sub.add_parser("open", help="Open/increase market position")
    open_p.add_argument("--size-usd", type=float, help="USD notional for size")
    open_p.add_argument("--collat", type=float, help="Collateral deposit (UI units)")

    add_p = sub.add_parser("add", help="Deposit collateral only")
    add_p.add_argument("--collat", type=float, help="Collateral deposit (UI units)")

    wdr_p = sub.add_parser("withdraw", help="Withdraw collateral only (USD)")
    wdr_p.add_argument("--withdraw-usd", type=float, help="USD to withdraw")

    combo = sub.add_parser("combo", help="Open → add → withdraw")
    combo.add_argument("--size-usd", type=float)
    combo.add_argument("--collat-open", type=float, default=0.0)
    combo.add_argument("--collat-add", type=float, default=0.0)
    combo.add_argument("--withdraw-usd", type=float, default=0.0)

    return p

# ─────────────────────────────────────────── Zero-arg defaults ───────────────────────────────────────────
def defaults_namespace() -> argparse.Namespace:
    repo_dir = guess_repo_dir()
    rpc = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    kp = guess_keypair_path()
    if not kp:
        fail("No keypair found. Provide ANCHOR_WALLET/KEYPAIR, or signer.txt with base58=..., or ~/.config/solana/id.json")

    # Live toggle: default to DRY-RUN unless JUP_PERPS_LIVE=1
    dry_run = os.getenv("JUP_PERPS_LIVE", "0") not in ("1", "true", "TRUE", "yes", "YES")
    max_price = float(os.getenv("JUP_PERPS_MAX_PRICE", "1000000"))

    ns = SimpleNamespace(
        # shared
        repo_dir=str(repo_dir),
        rpc=rpc,
        kp=kp,
        market="SOL",
        side="long",
        collat_mint=None,
        desired_mint=None,
        oracle_price=None,
        slip=None,
        max_price=max_price,
        min_price=None,
        dry_run=dry_run,
        timeout=900,  # allow time for a first npm install if needed
        # action + args
        action="open",
        size_usd=20.0,
        collat=12.0,
        withdraw_usd=None,
        collat_open=None,
        collat_add=None,
    )
    bar("Zero-arg mode", "🚀")
    kv("Repo dir", ns.repo_dir)
    kv("RPC", ns.rpc)
    kv("Keypair", ns.kp)
    kv("Action", "open (market)")
    kv("Market/Side", f"{ns.market}/{ns.side}")
    kv("Size USD", str(ns.size_usd))
    kv("Collateral", str(ns.collat))
    kv("Guardrail", f"--max-price {ns.max_price} (override with JUP_PERPS_MAX_PRICE)")
    kv("Dry-run", str(ns.dry_run))
    return ns

# ───────────────────────────────────────────── Main ─────────────────────────────────────────────
def main() -> None:
    ensure_npm_available()

    if len(sys.argv) == 1:
        # Zero-arg "just run it" path
        args = defaults_namespace()
        repo = Path(args.repo_dir)
        repo_sanity(repo)
        run_ts_action(args, "open", ["--size-usd", f"{args.size_usd}", "--collat", f"{args.collat}"])
        return

    # Argument-driven mode (explicit power-user path)
    parser = build_parser()
    args = parser.parse_args()

    # Fill missing with sensible defaults
    args.repo_dir = args.repo_dir or str(guess_repo_dir())
    args.rpc = args.rpc or os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    args.kp = args.kp or guess_keypair_path()
    if not args.kp:
        fail("No keypair found. Provide ANCHOR_WALLET/KEYPAIR, or signer.txt with base58=..., or ~/.config/solana/id.json.")

    # If no subcommand provided, default to open with defaults for size/collat
    if not args.action:
        args.action = "open"
        if getattr(args, "size_usd", None) is None: args.size_usd = 20.0
        if getattr(args, "collat", None)   is None: args.collat   = 12.0
    if not args.market: args.market = "SOL"
    if not args.side:   args.side   = "long"

    # If user gave no guardrail, apply wide default by side
    if not any([args.oracle_price and args.slip, args.max_price, args.min_price]):
        if (args.side or "long") == "long":
            args.max_price = float(os.getenv("JUP_PERPS_MAX_PRICE", "1000000"))
        else:
            args.min_price = 0.0  # extremely permissive

    repo = Path(args.repo_dir)
    repo_sanity(repo)

    if args.action == "open":
        ext = ["--size-usd", f"{args.size_usd}", "--collat", f"{args.collat}"]
        run_ts_action(args, "open", ext)

    elif args.action == "add":
        ext = ["--collat", f"{args.collat}"]
        run_ts_action(args, "add", ext)

    elif args.action == "withdraw":
        ext = ["--withdraw-usd", f"{args.withdraw_usd}"]
        run_ts_action(args, "withdraw", ext)

    elif args.action == "combo":
        bar("Combo scenario", "🎬")
        from time import sleep
        # Step 1: open/increase
        info("Step 1/3: open", "1️⃣")
        open_ext = ["--size-usd", f"{getattr(args,'size_usd',20.0)}", "--collat", f"{getattr(args,'collat_open',0.0)}"]
        tx1, pr1 = run_ts_action(args, "open", open_ext)
        sleep(2)
        # Step 2: add collateral
        info("Step 2/3: add collateral", "2️⃣")
        add_ext = ["--collat", f"{getattr(args,'collat_add',0.0)}"]
        tx2, pr2 = run_ts_action(args, "add", add_ext)
        sleep(2)
        # Step 3: withdraw
        info("Step 3/3: withdraw collateral", "3️⃣")
        wdr_ext = ["--withdraw-usd", f"{getattr(args,'withdraw_usd',0.0)}"]
        tx3, pr3 = run_ts_action(args, "withdraw", wdr_ext)
        bar("Summary", "🧾")
        kv("open.tx", tx1 or "(n/a)"); kv("open.request", pr1 or "(n/a)")
        kv("add.tx",  tx2 or "(n/a)"); kv("add.request",  pr2 or "(n/a)")
        kv("withdraw.tx", tx3 or "(n/a)"); kv("withdraw.request", pr3 or "(n/a)")
        ok("Combo scenario complete")

    else:
        fail(f"Unsupported action: {args.action}")

if __name__ == "__main__":
    try:
        main()
    except subprocess.TimeoutExpired:
        fail("Command timed out (increase --timeout).")
    except KeyboardInterrupt:
        fail("Interrupted by user.")
