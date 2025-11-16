from __future__ import annotations

"""
fun_core.client

Synchronous + async helpers used by:
- backend.core.fun_core.fun_console (via _FunAPI)
- Sonic Reporting cycle_footer_panel (🎉 footer line)

Design:
- Prefer real fun_core services via FunRegistry (httpx + TTL cache).
- Fall back to local seeds if anything fails (offline / rate‑limit / etc.).
- Safe to call from code that already has a running asyncio loop:
  we spin up a private event loop in a worker thread for blocking calls.
"""

import asyncio
import threading
from datetime import datetime
from typing import Tuple

from .models import FunContent, FunType
from .registry import FunRegistry
from .seeds import seed_for


def _normalize_kind(kind: str) -> FunType:
    raw = str(kind or "").lower()
    try:
        return FunType(raw)
    except Exception:  # noqa: BLE001
        return FunType.quote


async def fun_random(kind: str = "quote") -> FunContent:
    """
    Async helper: fetch a FunContent from the appropriate service.

    Used by Fun Console (which already runs an asyncio loop).
    """
    ft = _normalize_kind(kind)
    try:
        service = FunRegistry.by_type(ft)
    except Exception:  # noqa: BLE001
        # Registry missing or misconfigured: fall back to a seed.
        seed = seed_for(ft.value)
        return FunContent(
            type=ft,
            text=seed.text,
            source=seed.source,
            fetched_at=datetime.utcnow(),
        )
    return await service.get_random()


def _run_coro_sync(coro):
    """
    Run an async coroutine in a sync context.

    - If no event loop is running → use asyncio.run(coro).
    - If an event loop *is* running → spin up a private loop in a worker
      thread so we do not explode with "asyncio.run() called from a running
      event loop".
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop in this thread: safe to use asyncio.run().
        return asyncio.run(coro)

    result: dict = {}
    error: dict = {}

    def _worker() -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result["value"] = loop.run_until_complete(coro)
        except Exception as exc:  # noqa: BLE001
            error["exc"] = exc
        finally:
            try:
                loop.close()
            finally:
                asyncio.set_event_loop(None)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join()

    if "exc" in error:
        raise error["exc"]
    return result.get("value")


def fun_random_text_sync(mode: str = "auto") -> str:
    """
    Synchronous helper used by the Sonic Monitor footer.

    `mode`:
      - "auto" (default) → rotate quote/joke/trivia based on wall‑clock time.
      - "joke" / "quote" / "trivia" → explicit type.

    Safe to call inside or outside a running event loop.
    """
    if mode == "auto":
        # simple rotation: quote → joke → trivia
        sec = int(datetime.utcnow().timestamp())
        kind = ("quote", "joke", "trivia")[sec % 3]
    else:
        mk = str(mode or "").lower()
        kind = mk if mk in {"joke", "quote", "trivia"} else "quote"

    try:
        content = _run_coro_sync(fun_random(kind))
        text = getattr(content, "text", "") or ""
        if text.strip():
            return text.strip()
    except Exception:
        pass

    # last‑ditch fallback: local seed
    return seed_for(kind).text


def fun_random_text() -> str:
    """
    Backwards‑compatible wrapper expected by _FunAPI.fun_random_text().
    """
    return fun_random_text_sync("auto")


def get_fun_line(loop_counter: int = 0) -> Tuple[str, str]:
    """
    Convenience helper used by:
      - Fun Console (via FUN.get_fun_line)
      - Sonic footer (via cycle_footer_panel._resolve_fun_line)

    Returns:
      (text, meta) where meta is a simple "type|source" string for debugging.
    """
    try:
        idx = int(loop_counter)
    except Exception:  # noqa: BLE001
        idx = 0

    # Rotate type by loop counter for a bit of variety across cycles.
    kind = ("quote", "joke", "trivia")[idx % 3]

    try:
        content = _run_coro_sync(fun_random(kind))
        text = getattr(content, "text", "") or ""
        if text.strip():
            ctype = getattr(content, "type", kind)
            source = getattr(content, "source", "unknown")
            meta = f"{getattr(ctype, 'value', str(ctype))}|{source}"
            return text.strip(), meta
    except Exception:
        pass

    seed = seed_for(kind)
    return seed.text, f"{kind}|seed"


__all__ = [
    "fun_random",
    "fun_random_text_sync",
    "fun_random_text",
    "get_fun_line",
]
