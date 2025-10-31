"""
GMX Core Console (Phase 1)
==========================

Purpose
-------
Quick, dependency-free CLI to validate that the GMX Core package is installed,
importable, and that config files are present. Networking is implemented in
later phases.

Usage
-----
python -m backend.core.gmx_core.console.console --help
python -m backend.core.gmx_core.console.console ping
python -m backend.core.gmx_core.console.console config --show
python -m backend.core.gmx_core.console.console smoke
"""
import argparse
import os
from pathlib import Path
from .menus import header, kv


PKG_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PKG_ROOT / "config"
DEFAULT_CONFIG = CONFIG_DIR / "gmx_chains.yaml"


def cmd_ping(_: argparse.Namespace) -> int:
    header("GMX Core Console")
    print("status: alive ✅")
    kv("package", str(PKG_ROOT))
    kv("config dir", str(CONFIG_DIR))
    kv("default config", str(DEFAULT_CONFIG))
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    header("GMX Core Config")
    cfg_path = Path(args.path) if args.path else DEFAULT_CONFIG
    kv("config path", str(cfg_path))
    if not cfg_path.exists():
        print("⚠️  file not found; create it from the Phase 1 template.")
        return 2
    print("\n--- file contents ---")
    print(cfg_path.read_text(encoding="utf-8"))
    print("--- end ---")
    return 0


def cmd_smoke(_: argparse.Namespace) -> int:
    header("GMX Core Smoke Test")
    problems = 0

    # 1) Imports exist?
    try:
        from ..services.position_source import GMXPositionSource  # noqa
        from ..models.types import GMXPosition, NormalizedPosition  # noqa
        from ..dl.positions_writer import write_positions  # noqa
    except Exception as exc:
        print(f"import error: {exc}")
        problems += 1
    else:
        print("imports: ok ✅")

    # 2) Config file exists?
    if not DEFAULT_CONFIG.exists():
        print(f"config: missing ({DEFAULT_CONFIG})")
        problems += 1
    else:
        print("config: ok ✅")

    # 3) Markets seeds present?
    seeds = CONFIG_DIR / "markets_seeds.json"
    if not seeds.exists():
        print(f"markets seeds: missing ({seeds})")
        problems += 1
    else:
        print("markets seeds: ok ✅")

    print("\nresult:", "PASS ✅" if problems == 0 else "FAIL ❌")
    return problems


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gmx-console", description="GMX Core console")
    sub = p.add_subparsers(dest="cmd", required=True)

    s_ping = sub.add_parser("ping", help="basic liveness check")
    s_ping.set_defaults(func=cmd_ping)

    s_cfg = sub.add_parser("config", help="config utilities")
    s_cfg.add_argument("--path", help="path to gmx_chains.yaml (default: package template)")
    s_cfg.add_argument("--show", action="store_true", help="print file contents")
    s_cfg.set_defaults(func=cmd_config)

    s_smoke = sub.add_parser("smoke", help="import+files smoke test")
    s_smoke.set_defaults(func=cmd_smoke)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Backward compatibility: `config` requires --show to print.
    if args.cmd == "config" and not getattr(args, "show", False):
        print("Tip: add --show to print the YAML contents.")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
