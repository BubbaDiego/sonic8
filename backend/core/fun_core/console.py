from __future__ import annotations
"""
Shim entrypoint so `python -m backend.core.fun_core.console` launches the real Fun Console.

This defers to `backend.core.fun_core.fun_console.run()` (preferred),
and falls back to a minimal one-shot if fun_console is missing.
"""


def _fallback_once() -> None:
    # Minimal, just to prove wiring if fun_console isn't present.
    print("\n🎛️  Sonic Fun Console\n")
    print("No `fun_console` module found. Tip: ensure backend/core/fun_core/fun_console.py exists.")
    print("You can still test the banner by setting SONIC_FUN_MODE=rotate.")
    input("\nPress ENTER to exit…")


def run() -> None:
    try:
        from .fun_console import run as _run
    except Exception:
        _fallback_once()
        return
    _run()


if __name__ == "__main__":
    run()
