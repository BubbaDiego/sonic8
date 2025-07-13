"""Environment utilities."""

import os


def _resolve_env(value, env_key):
    """Return ``value`` or fall back to the ``env_key`` environment variable.

    Strings wrapped like ``"${VAR}"`` are also resolved from ``VAR``.
    """

    if value is None or value == "":
        return os.getenv(env_key)
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return os.getenv(value[2:-1])
    return value


__all__ = ["_resolve_env"]

