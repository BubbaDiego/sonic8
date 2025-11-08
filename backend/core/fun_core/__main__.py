from __future__ import annotations

try:
    from .console import run as _run
except Exception:

    def _run() -> None:  # pragma: no cover - fallback for missing console module
        print("No fun console available (backend.core.fun_core.console missing).")
        print("Tip: LaunchPad → Fun Console will try alternate modules or seeds.")


if __name__ == "__main__":
    _run()
