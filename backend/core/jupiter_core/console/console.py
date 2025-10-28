from __future__ import annotations

import sys
from typing import Callable, Dict

from ..services import JupiterService
from . import menus
from .views import panel


def _menu(svc: JupiterService) -> None:
    actions: Dict[str, tuple[str, Callable[[], None]]] = {
        "1": ("Preflight / Config", lambda: menus.show_preflight(svc)),
        "2": ("Quote (legacy /swap/v1/quote)", lambda: menus.menu_quote(svc)),
        "3": ("Ultra Order (build tx)", lambda: menus.menu_ultra_order(svc)),
        "4": ("Ultra Execute (paste SIGNED b64)", lambda: menus.menu_ultra_execute(svc)),
        "5": ("Trigger: List Orders", lambda: menus.menu_trigger_list(svc)),
        "6": ("Trigger: Create", lambda: menus.menu_trigger_create(svc)),
        "7": ("Trigger: Cancel", lambda: menus.menu_trigger_cancel(svc)),
        "8": ("Wallet: Load signer.txt & Show Address", menus.menu_wallet_show),
        "9": ("Balances: SOL, WSOL, WETH, WBTC, USDC", menus.menu_wallet_balances),
        "10": ("Positions: Jupiter Perps (probe API)", menus.menu_positions_probe),
        "0": ("Exit", lambda: sys.exit(0)),
    }
    while True:
        print("\n══════════════════════════════════════════════════════════════")
        print(" 🚀 Jupiter Core Console")
        print("══════════════════════════════════════════════════════════════")
        for k in sorted(actions.keys(), key=lambda x: int(x) if x.isdigit() else 999):
            print(f" {k}. {actions[k][0]}")
        choice = input("\n→ Select: ").strip()
        action = actions.get(choice)
        if not action:
            panel("Invalid", f"Unknown choice: {choice}")
            continue
        try:
            action[1]()
        except SystemExit:
            raise
        except Exception as exc:  # pragma: no cover - runtime feedback
            panel("💥 Exception", f"{type(exc).__name__}: {exc}")


def main() -> None:
    svc = JupiterService()
    menus.show_preflight(svc)
    _menu(svc)


if __name__ == "__main__":
    main()
