from __future__ import annotations

import asyncio
import os
import textwrap
from datetime import datetime
from typing import Dict, List, Tuple

from .client import fun_random, fun_random_text, get_fun_line
from .models import FunType
from .seeds import seed_for

BANNER = r"""
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃   🎛️  Sonic Fun Console             🃏  ✨  ❓              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
"""


def menu_text(offline: bool) -> str:
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


PROVIDERS: Dict[FunType, List[Tuple[str, str, Dict[str, str]]]] = {
    FunType.joke: [
        ("jokeapi", "https://v2.jokeapi.dev/joke/Any?type=single&safe-mode=", {}),
        ("official-joke", "https://official-joke-api.appspot.com/random_joke", {}),
        ("icanhazdadjoke", "https://icanhazdadjoke.com/", {"Accept": "application/json"}),
    ],
    FunType.quote: [
        ("zenquotes", "https://zenquotes.io/api/random", {}),
        ("quotable", "https://api.quotable.io/random", {}),
    ],
    FunType.trivia: [
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


async def _fetch_text(ftype: FunType, offline: bool):
    if offline:
        return seed_for(ftype)
    return await fun_random(ftype.value)


async def show_joke(offline: bool) -> None:
    item = await _fetch_text(FunType.joke, offline)
    print(f"\n[{_stamp()}]  🃏  {item.text}  · source={item.source}")


async def show_quote(offline: bool) -> None:
    item = await _fetch_text(FunType.quote, offline)
    print(f"\n[{_stamp()}]  ✨  {item.text}  · source={item.source}")


async def show_trivia(offline: bool) -> None:
    item = await _fetch_text(FunType.trivia, offline)
    print(f"\n[{_stamp()}]  ❓  {item.text}")
    input("   Press [Enter] to reveal…")


async def provider_status() -> None:
    try:
        import httpx  # shared by fun_core
    except Exception:
        print("\nhttpx not available.")
        return
    print("\nProviders status (simple GET):")
    async with httpx.AsyncClient(timeout=5) as client:
        for t, targets in PROVIDERS.items():
            ok = 0
            for name, url, headers in targets:
                try:
                    r = await client.get(url, headers=headers)
                    ok += 1 if r.status_code < 500 else 0
                except Exception:
                    pass
            print(f"  {t.value:<7} {ok}/{len(targets)} reachable")
    print("")


async def prewarm_caches(n: int = 5) -> None:
    total = 0
    for t in (FunType.joke, FunType.quote, FunType.trivia):
        hits = 0
        for _ in range(max(1, n)):
            try:
                item = await fun_random(t.value)
                hits += 1 if item else 0
            except Exception:
                pass
        total += hits
        print(f"  {t.value:<7}: fetched {hits}/{n}")
    print(f"Done. Cached pulls: {total}\n")


async def auto_rotate(interval_s: float, offline: bool) -> None:
    seq = (FunType.joke, FunType.quote, FunType.trivia)
    i = 0
    print("")
    while True:
        t = seq[i % len(seq)]
        i += 1
        if t == FunType.joke:
            await show_joke(offline)
        elif t == FunType.quote:
            await show_quote(offline)
        else:
            await show_trivia(offline)
        await asyncio.sleep(max(1.0, float(interval_s)))


async def main_loop() -> None:
    offline = False
    while True:
        _clear()
        print(BANNER)
        print(textwrap.dedent(menu_text(offline)))
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
