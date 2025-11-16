from __future__ import annotations

"""
Local seed content for fun_core.

Shared between:
- backend.core.fun_core.fun_console (fallback)
- backend.core.fun_core.client (fallback)
- Anything else that wants a cheap, offline one-liner.
"""

from types import SimpleNamespace
from typing import Dict

_POOL: Dict[str, str] = {
    "joke": "I told my code to clean itself. It said it is not a janitor.",
    "quote": "In code we trust; in logs we verify.",
    "trivia": "Trivia: HTTP 418 is 'I am a teapot'.",
}


def seed_for(kind: str) -> SimpleNamespace:
    """
    Return a simple object with `.text` and `.source` fields.

    Unknown kinds fall back to a neutral dash.
    """
    key = str(kind or "").lower()
    text = _POOL.get(key, "—")
    return SimpleNamespace(text=text, source="seed/fun_core")
