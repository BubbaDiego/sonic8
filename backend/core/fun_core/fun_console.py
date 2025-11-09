from __future__ import annotations
"""
Fun Console — numbered TUI for jokes / quotes / trivia + status, prewarm, offline toggle.

Runs even if your fun_core layout differs:
- prefers backend.core.fun_core.client
- falls back to backend.core.fun_core.fun_core or .api
- falls back to local seeds if no client is available

Run:
  python -m backend.core.fun_core.fun_console
  (also launched via the console shim: python -m backend.core.fun_core.console)
"""

# --- Robust import shim for direct-file execution (PyCharm, etc.) ---
if __package__ is None or __package__ == "":
    import sys, pathlib

    _root = str(pathlib.Path(__file__).resolve().parents[3])
    if _root not in sys.path:
        sys.path.insert(0, _root)

import asyncio
import os
import textwrap
import time
from datetime import datetime
from types import SimpleNamespace
from typing import Dict, List, Tuple

from backend.core.fun_core.transitions.lab_console import main as transitions_lab


# ──────────────────────────────────────────────────────────────────────────────
# resolve fun_core implementation
# ──────────────────────────────────────────────────────────────────────────────
def _load_fun_module():
    import importlib

    for name in (
        "backend.core.fun_core.client",  # preferred
        "backend.core.fun_core.fun_core",  # older
        "backend.core.fun_core.api",  # alt
    ):
        try:
            return importlib.import_module(name)
        except Exception:
            continue
    return None


def _seed_for(kind: str) -> SimpleNamespace:
    try:
        from backend.core.fun_core.seeds import seed_for as _sf  # type: ignore

        return _sf(kind)
    except Exception:
        pool = {
            "joke": "I told my code to clean itself. It said it’s not a janitor.",
            "quote": "In code we trust; in logs we verify.",
            "trivia": "Trivia: HTTP 418 is “I’m a teapot.”",
        }
        return SimpleNamespace(text=pool.get(kind, "—"), source="seed/fallback")


class _FunAPI:
    def __init__(self) -> None:
        self.mod = _load_fun_module()

    async def fun_random(self, kind: str):
        if self.mod:
            fn = getattr(self.mod, "fun_random", None)
            if callable(fn):
                if asyncio.iscoroutinefunction(fn):
                    return await fn(kind)
                try:
                    return fn(kind)  # sync
                except Exception:
                    pass
        return _seed_for(kind)

    def fun_random_text(self) -> str:
        if self.mod:
            fn = getattr(self.mod, "fun_random_text", None)
            if callable(fn):
                try:
                    return str(fn()).strip()
                except Exception:
                    pass
        return _seed_for("quote").text

    def get_fun_line(self, loop_counter: int = 0):
        if self.mod:
            fn = getattr(self.mod, "get_fun_line", None)
            if callable(fn):
                try:
                    res = fn(int(loop_counter))
                    if isinstance(res, tuple) and res and isinstance(res[0], str):
                        return res
                    if isinstance(res, dict):
                        txt = res.get("text") or res.get("fun_line") or res.get("line") or "—"
                        return (str(txt).strip(), res.get("meta", ""))
                    if isinstance(res, str):
                        return (res.strip(), "")
                except Exception:
                    pass
        seed = _seed_for("quote")
        return (seed.text, "seed|fallback")


FUN = _FunAPI()

# ──────────────────────────────────────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────────────────────────────────────
BANNER = r"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   🎛️  Sonic Fun Console             🃏  ✨  ❓              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
"""

MENU = """
  1) 🃏  Joke
  2) ✨  Quote
  3) ❓  Trivia (press [Enter] to reveal answer)
  4) 🔁  Auto-rotate (joke→quote→trivia) every N seconds
  5) 🧭  Provider status (reachability & latency)
  6) 🔥  Pre-warm caches (pull N items per type)
  7) 🧰  Offline mode (seeds only): {offline}
  T) 🌀  Transitions Lab (animations)
  0) 🚪  Quit
"""

PROVIDERS: Dict[str, List[Tuple[str, str, Dict[str, str]]]] = {
    "joke": [
        ("jokeapi", "https://v2.jokeapi.dev/joke/Any?type=single&safe-mode=", {"Accept": "application/json"}),
        ("official-joke", "https://official-joke-api.appspot.com/random_joke", {}),
        ("icanhazdadjoke", "https://icanhazdadjoke.com/", {"Accept": "application/json"}),
    ],
    "quote": [
        ("zenquotes", "https://zenquotes.io/api/random", {}),
        ("quotable", "https://api.quotable.io/random", {}),
    ],
    "trivia": [
        ("opentdb", "https://opentdb.com/api.php?amount=1", {}),
        ("jservice", "https://jservice.io/api/random", {}),
    ],
}


def _stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clear() -> None:
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        pass


async def _fetch_text(kind: str, offline: bool):
    if offline:
        return _seed_for(kind)
    return await FUN.fun_random(kind)


async def show_joke(offline: bool) -> None:
    item = await _fetch_text("joke", offline)
    print(f"\n[{_stamp()}]  🃏  {item.text}  · source={getattr(item, 'source', 'unknown')}")


async def show_quote(offline: bool) -> None:
    item = await _fetch_text("quote", offline)
    print(f"\n[{_stamp()}]  ✨  {item.text}  · source={getattr(item, 'source', 'unknown')}")


async def show_trivia(offline: bool) -> None:
    item = await _fetch_text("trivia", offline)
    print(f"\n[{_stamp()}]  ❓  {item.text}")
    input("   Press [Enter] to reveal…")


async def provider_status(timeout: float = 5.0) -> None:
    try:
        import httpx
    except Exception:
        print("\nhttpx not available.")
        return
    print("\nProviders status (simple GET):")
    async with httpx.AsyncClient(timeout=timeout) as client:
        rows: List[Tuple[str, str, str, float, str]] = []
        for kind, endpoints in PROVIDERS.items():
            for (name, url, headers) in endpoints:
                t0 = time.perf_counter()
                ok, err = True, ""
                try:
                    r = await client.get(url, headers=headers)
                    ok = 200 <= r.status_code < 500
                    if not ok:
                        err = f"HTTP {r.status_code}"
                except Exception as e:
                    ok, err = False, repr(e)
                dt = (time.perf_counter() - t0) * 1000.0
                rows.append((kind, name, "OK" if ok else "FAIL", dt, err[:120]))
        print("\n  TYPE     PROVIDER           STATUS   LAT(ms)   NOTE")
        print("  -------  -----------------  ------   -------   ----")
        for t, name, status, ms, note in rows:
            print(f"  {t:<7}  {name:<17}  {status:<6}   {ms:>7.1f}   {note}")
    print()


async def prewarm_caches(n: int = 5) -> None:
    print(f"\nPre-warming caches with {n} pulls per type…")
    total = 0
    for kind in ("joke", "quote", "trivia"):
        hits = 0
        for _ in range(max(1, n)):
            try:
                item = await FUN.fun_random(kind)
                if item and getattr(item, "text", None):
                    hits += 1
            except Exception:
                pass
        total += hits
        print(f"  {kind:<7}: fetched {hits}/{n}")
    print(f"Done. Cached pulls: {total}\n")


async def auto_rotate(interval_s: float, offline: bool) -> None:
    seq = ("joke", "quote", "trivia")
    i = 0
    print("")
    while True:
        kind = seq[i % len(seq)]
        i += 1
        if kind == "joke":
            await show_joke(offline)
        elif kind == "quote":
            await show_quote(offline)
        else:
            await show_trivia(offline)
        await asyncio.sleep(max(1.0, float(interval_s)))


async def main_loop() -> None:
    offline = False
    while True:
        _clear()
        print(BANNER)
        print(textwrap.dedent(MENU.format(offline="ON" if offline else "OFF")))
        sel = input("Select: ").strip().lower()

        if sel == "1":
            await show_joke(offline)
        elif sel == "2":
            await show_quote(offline)
        elif sel == "3":
            await show_trivia(offline)
        elif sel == "4":
            raw = input("Interval seconds (default 30): ").strip()
            try:
                n = float(raw) if raw else 30.0
            except ValueError:
                n = 30.0
            await auto_rotate(n, offline)
        elif sel == "5":
            await provider_status()
        elif sel == "6":
            raw = input("Pull how many per type (default 5): ").strip()
            try:
                n = int(raw) if raw else 5
            except ValueError:
                n = 5
            await prewarm_caches(n=n)
        elif sel == "7":
            offline = not offline
            print(f"\nOffline mode is now {'ON' if offline else 'OFF'}.\n")
        elif sel in ("t", "transitions", "lab"):
            transitions_lab()
        elif sel in ("0", "q", "quit", "exit"):
            print("\nbye 👋\n")
            return
        else:
            print("\nInvalid choice.")
        input("\nPress [Enter] to continue…")


def run() -> None:
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\nbye 👋")


if __name__ == "__main__":
    run()
