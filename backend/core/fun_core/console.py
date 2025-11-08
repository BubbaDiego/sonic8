from __future__ import annotations
"""
Sonic Fun Console (robust import version)
- Works whether fun_core exposes .client, .fun_core, or .api
- Falls back to local seeds if no client is available
Run via:
  python -m backend.core.fun_core
  or
  python -m backend.core.fun_core.console
"""

import asyncio
import importlib
import os
import textwrap
from datetime import datetime
from types import SimpleNamespace


# ──────────────────────────────────────────────────────────────────────────────
# Dynamic fun_core resolver (client → fun_core → api → seeds fallback)
# ──────────────────────────────────────────────────────────────────────────────


def _load_fun_module():
    for name in (
        "backend.core.fun_core.client",  # preferred if present
        "backend.core.fun_core.fun_core",  # older name
        "backend.core.fun_core.api",  # some branches
    ):
        try:
            return importlib.import_module(name)
        except Exception:
            continue
    return None


def _seed_for(kind: str) -> SimpleNamespace:
    try:
        from .seeds import seed_for as _seed_for  # type: ignore

        return _seed_for(kind)
    except Exception:
        pool = {
            "joke": "I told my code to clean itself. It said it's not a janitor.",
            "quote": "In code we trust; in logs we verify.",
            "trivia": "Trivia: HTTP 418 is 'I'm a teapot.'",
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
                    return fn(kind)
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
                        txt = (
                            res.get("text")
                            or res.get("fun_line")
                            or res.get("line")
                            or "—"
                        )
                        return (str(txt).strip(), res.get("meta", ""))
                    if isinstance(res, str):
                        return (res.strip(), "")
                except Exception:
                    pass
        seed = _seed_for("quote")
        return (seed.text, "seed|fallback")


FUN = _FunAPI()

# ──────────────────────────────────────────────────────────────────────────────
# UI helpers
# ──────────────────────────────────────────────────────────────────────────────


BANNER = r"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   🎛️  Sonic Fun Console             🃏  ✨  ❓              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
"""


def _stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clear() -> None:
    try:
        os.system("cls" if os.name == "nt" else "clear")
    except Exception:
        pass


def _menu_text(offline: bool) -> str:
    net = "🛰️ OFF" if offline else "🌐 ON "
    return f"""
  1) 🃏  Joke
  2) ✨  Quote
  3) ❓  Trivia (press [Enter] to reveal answer)
  4) 🔁  Auto-rotate (joke→quote→trivia) every N seconds
  5) 🧭  Provider status (reachability & latency)
  6) 🔥  Pre-warm caches (pull N items per type)
  7) 🧰  Offline mode (seeds only): {net}
  0) 🚪  Quit
"""


PROVIDERS = {
    "joke": [
        ("jokeapi", "https://v2.jokeapi.dev/joke/Any?type=single&safe-mode="),
        ("official-joke", "https://official-joke-api.appspot.com/random_joke"),
        ("icanhazdadjoke", "https://icanhazdadjoke.com/"),
    ],
    "quote": [
        ("zenquotes", "https://zenquotes.io/api/random"),
        ("quotable", "https://api.quotable.io/random"),
    ],
    "trivia": [
        ("opentdb", "https://opentdb.com/api.php?amount=1"),
        ("jservice", "https://jservice.io/api/random"),
    ],
}


# ──────────────────────────────────────────────────────────────────────────────
# Actions
# ──────────────────────────────────────────────────────────────────────────────


async def _fetch_text(kind: str, offline: bool):
    if offline:
        return _seed_for(kind)
    return await FUN.fun_random(kind)


async def show_joke(offline: bool) -> None:
    item = await _fetch_text("joke", offline)
    print(
        f"\n[{_stamp()}]  🃏  {item.text}  · source={getattr(item, 'source', 'unknown')}"
    )


async def show_quote(offline: bool) -> None:
    item = await _fetch_text("quote", offline)
    print(
        f"\n[{_stamp()}]  ✨  {item.text}  · source={getattr(item, 'source', 'unknown')}"
    )


async def show_trivia(offline: bool) -> None:
    item = await _fetch_text("trivia", offline)
    print(f"\n[{_stamp()}]  ❓  {item.text}")
    input("   Press [Enter] to reveal…")


async def provider_status() -> None:
    try:
        import httpx
    except Exception:
        print("\nhttpx not available.")
        return
    print("\nProviders status (simple GET):")
    async with httpx.AsyncClient(timeout=5) as client:
        for kind, targets in PROVIDERS.items():
            ok = 0
            for name, url in targets:
                try:
                    response = await client.get(url, headers={"Accept": "application/json"})
                    ok += 1 if response.status_code < 500 else 0
                except Exception:
                    pass
            print(f"  {kind:<7} {ok}/{len(targets)} reachable")
    print("")


async def prewarm_caches(n: int = 5) -> None:
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


# ──────────────────────────────────────────────────────────────────────────────
# Main Loop
# ──────────────────────────────────────────────────────────────────────────────


async def main_loop() -> None:
    offline = False
    while True:
        _clear()
        print(BANNER)
        print(textwrap.dedent(_menu_text(offline)))
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
                interval = float(raw) if raw else 30.0
            except ValueError:
                interval = 30.0
            await auto_rotate(interval, offline)
        elif sel == "5":
            await provider_status()
        elif sel == "6":
            raw = input("Pull how many per type (default 5): ").strip()
            try:
                count = int(raw) if raw else 5
            except ValueError:
                count = 5
            await prewarm_caches(n=count)
        elif sel == "7":
            offline = not offline
            print(f"\nOffline mode is now {'ON' if offline else 'OFF'}.\n")
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
