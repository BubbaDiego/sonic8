#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jupiter Perps — CLI Smoke Tester (Python)
Runs the TypeScript CLIs we added in jupiter-perps-anchor-idl-parsing:
  - perps_open_market.ts
  - perps_add_collateral.ts
  - perps_withdraw_collateral.ts

Actions:
  open        → open/increase market position (+ optional collateral)
  add         → deposit collateral only (size=0)
  withdraw    → withdraw collateral only (USD notional)
  combo       → run open → add → withdraw (sequential)

Example:
  python backend/scripts/perps_cli_smoke_test.py \
    --repo-dir "C:\\jupiter-perps-anchor-idl-parsing" \
    --rpc "https://api.mainnet-beta.solana.com" \
    --kp  "C:\\sonic5\\keys\\trader.json" \
    --market SOL --side long \
    --oracle-price 150 --slip 0.02 \
    open --size-usd 5 --collat 0.02
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional

# ──────────────────────────────────────────── Pretty logging ────────────────────────────────────────────
def bar(title: str, emoji: str = "🧭") -> None:
    line = "─" * max(12, 60 - len(title))
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
    print(f"  • {label.ljust(18)} = {value}")

# ───────────────────────────────────────────── Helpers ─────────────────────────────────────────────
B58_RE = r"[1-9A-HJ-NP-Za-km-z]{32,48}"

def find_tx_sig(text: str) -> Optional[str]:
    m = re.search(r"Tx sent:\s*([A-Za-z0-9]+)", text)
    return m.group(1) if m else None

def find_pos_request(text: str) -> Optional[str]:
    m = re.search(r"PositionRequest\s*=\s*(" + B58_RE + r")", text)
    return m.group(1) if m else None

def run(
    cmd: List[str],
    cwd: Path,
    timeout: int = 240,
    env: Optional[dict] = None,
) -> Tuple[int, str, str]:
    """Run a command, capture stdout/stderr as text."""
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        shell=False,
        env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr

def ensure_npm_available() -> None:
    if shutil.which("npm") is None:
        fail("npm was not found on PATH. Install Node/npm or open a shell where npm is available.")

def ensure_ts_node(repo: Path) -> None:
    """Best-effort check that ts-node is accessible."""
    ts_node_bin = repo / "node_modules" / ".bin" / "ts-node"
    if ts_node_bin.exists() or shutil.which("ts-node") is not None:
        return
    warn("ts-node not found locally; relying on npx to download on first use.")

def ensure_tsx(repo: Path) -> None:
    """Best-effort check that tsx is accessible."""
    tsx_bin = repo / "node_modules" / ".bin" / "tsx"
    if tsx_bin.exists() or shutil.which("tsx") is not None:
        return
    warn("tsx not found locally; relying on npx to download on first use.")

def repo_sanity(repo_dir: Path) -> None:
    pkg = repo_dir / "package.json"
    ex1 = repo_dir / "src" / "examples" / "perps_open_market.ts"
    ex2 = repo_dir / "src" / "examples" / "perps_add_collateral.ts"
    ex3 = repo_dir / "src" / "examples" / "perps_withdraw_collateral.ts"
    if not pkg.exists():
        fail(f"package.json not found in {repo_dir}")
    for p in [ex1, ex2, ex3]:
        if not p.exists():
            fail(f"Expected example missing: {p}")

def common_args(ns: argparse.Namespace) -> List[str]:
    args = [
        "--rpc", ns.rpc,
        "--kp", ns.kp,
        "--market", ns.market,
        "--side", ns.side,
    ]
    # guardrail selection
    if ns.oracle_price is not None and ns.slip is not None:
        args += ["--oracle-price", f"{ns.oracle_price}", "--slip", f"{ns.slip}"]
    elif ns.max_price is not None:
        args += ["--max-price", f"{ns.max_price}"]
    elif ns.min_price is not None:
        args += ["--min-price", f"{ns.min_price}"]
    else:
        warn("No explicit guardrail flags provided at top-level; per-action flags may supply them.")
    if ns.collat_mint:
        args += ["--collat-mint", ns.collat_mint]
    if ns.desired_mint:
        args += ["--desired-mint", ns.desired_mint]
    if ns.dry_run:
        args += ["--dry-run"]
    return args

def try_runners(ns: argparse.Namespace, ts_path: str, extra: List[str]) -> Tuple[int, str, str]:
    repo = Path(ns.repo_dir)
    env = os.environ.copy()
    env["TS_NODE_TRANSPILE_ONLY"] = "1"

    base_args = common_args(ns)

    # 1) node --loader ts-node/esm  (+ CJS-like extension resolution shim)
    ensure_ts_node(repo)
    cmd1 = [
        "node",
        "--loader", "ts-node/esm",
        "--experimental-specifier-resolution=node",
        ts_path,
    ] + base_args + extra
    bar("Runner: node --loader ts-node/esm", "🧪")
    code, out, err = run(cmd1, cwd=repo, timeout=ns.timeout, env=env)
    out = out or ""; err = err or ""
    if code == 0:
        return code, out, err
    if "ERR_UNKNOWN_FILE_EXTENSION" not in (out + err):
        return code, out, err

    # 2) npx ts-node --transpile-only
    cmd2 = ["npx", "ts-node", "--transpile-only", ts_path] + base_args + extra
    bar("Runner: npx ts-node --transpile-only", "🧪")
    code, out, err = run(cmd2, cwd=repo, timeout=ns.timeout, env=env)
    out = out or ""; err = err or ""
    if code == 0:
        return code, out, err
    if "ERR_UNKNOWN_FILE_EXTENSION" not in (out + err):
        return code, out, err

    # 3) npx tsx
    ensure_tsx(repo)
    cmd3 = ["npx", "tsx", ts_path] + base_args + extra
    bar("Runner: npx tsx", "🧪")
    code, out, err = run(cmd3, cwd=repo, timeout=ns.timeout, env=env)
    return code, (out or ""), (err or "")

def run_ts_action(ns: argparse.Namespace, action: str, extra: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (tx_sig, position_request)
    """
    mapping = {
        "open":      "src/examples/perps_open_market.ts",
        "add":       "src/examples/perps_add_collateral.ts",
        "withdraw":  "src/examples/perps_withdraw_collateral.ts",
    }
    ts_path = mapping.get(action)
    if not ts_path:
        fail(f"Unknown action {action}")

    bar(f"Execute: {action}", "📤")
    info("TS module:", "🧾")
    print("   ", ts_path)

    code, out, err = try_runners(ns, ts_path, extra)
    print()
    if out.strip():
        bar("stdout", "🟢")
        print(out)
    if err.strip():
        bar("stderr", "🟠")
        print(err)

    if code != 0:
        fail(f"{action} failed with exit code {code}")

    tx = find_tx_sig(out) or find_tx_sig(err)
    pr = find_pos_request(out) or find_pos_request(err)
    if tx:
        ok(f"{action} → signature: {tx}")
    else:
        warn(f"{action} → no signature found (dry-run or simulate?)")
    if pr:
        ok(f"{action} → position request: {pr}")
    else:
        warn(f"{action} → no position request address detected")

    return tx, pr

# ───────────────────────────────────────────── CLI ─────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Smoke-test the Jupiter Perps TS CLI via npm run script",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # where the TS repo lives
    p.add_argument("--repo-dir", required=True, help="Path to jupiter-perps-anchor-idl-parsing repo")
    # chain & wallet
    p.add_argument("--rpc", required=True, help="RPC URL")
    p.add_argument("--kp", required=True, help="Path to keypair (JSON array or base58 secret)")
    # market config
    p.add_argument("--market", required=True, choices=["SOL", "ETH", "BTC"], help="Market asset")
    p.add_argument("--side", required=True, choices=["long", "short"], help="Position side")
    p.add_argument("--collat-mint", help="Override collateral mint")
    p.add_argument("--desired-mint", help="Receiving mint for withdraw (defaults to collateral mint)")
    # guardrail options
    p.add_argument("--oracle-price", type=float, help="Oracle/mark price in USD")
    p.add_argument("--slip", type=float, help="Fractional slippage for guardrail (e.g., 0.02)")
    p.add_argument("--max-price", type=float, help="Explicit max price (LONG)")
    p.add_argument("--min-price", type=float, help="Explicit min price (SHORT)")
    # behavior
    p.add_argument("--dry-run", action="store_true", help="Use TS CLI --dry-run")
    p.add_argument("--timeout", type=int, default=240, help="Per-command timeout (seconds)")

    sub = p.add_subparsers(dest="action", required=True)

    open_p = sub.add_parser("open", help="Open/increase market position")
    open_p.add_argument("--size-usd", type=float, required=True, help="USD notional for size")
    open_p.add_argument("--collat", type=float, default=0.0, help="Collateral deposit (UI units)")

    add_p = sub.add_parser("add", help="Deposit collateral only")
    add_p.add_argument("--collat", type=float, required=True, help="Collateral deposit (UI units)")

    wdr_p = sub.add_parser("withdraw", help="Withdraw collateral only (USD)")
    wdr_p.add_argument("--withdraw-usd", type=float, required=True, help="USD to withdraw")

    combo = sub.add_parser("combo", help="Open → add → withdraw")
    combo.add_argument("--size-usd", type=float, required=True)
    combo.add_argument("--collat-open", type=float, default=0.0)
    combo.add_argument("--collat-add", type=float, default=0.0)
    combo.add_argument("--withdraw-usd", type=float, default=0.0)

    return p

def main() -> None:
    args = build_parser().parse_args()

    bar("Preflight", "🔎")
    ensure_npm_available()
    repo = Path(args.repo_dir).resolve()
    kv("Repo dir", str(repo))
    repo_sanity(repo)
    ok("Repo checks passed")

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

        # Step 1: open/increase
        info("Step 1/3: open", "1️⃣")
        open_ext = ["--size-usd", f"{args.size_usd}", "--collat", f"{args.collat_open}"]
        tx1, pr1 = run_ts_action(args, "open", open_ext)

        # Step 2: add collateral
        info("Step 2/3: add collateral", "2️⃣")
        add_ext = ["--collat", f"{args.collat_add}"]
        tx2, pr2 = run_ts_action(args, "add", add_ext)

        # Step 3: withdraw
        info("Step 3/3: withdraw collateral", "3️⃣")
        wdr_ext = ["--withdraw-usd", f"{args.withdraw_usd}"]
        tx3, pr3 = run_ts_action(args, "withdraw", wdr_ext)

        bar("Summary", "🧾")
        kv("open.tx", tx1 or "(n/a)")
        kv("open.request", pr1 or "(n/a)")
        kv("add.tx", tx2 or "(n/a)")
        kv("add.request", pr2 or "(n/a)")
        kv("withdraw.tx", tx3 or "(n/a)")
        kv("withdraw.request", pr3 or "(n/a)")
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
