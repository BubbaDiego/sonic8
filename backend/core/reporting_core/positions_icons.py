from __future__ import annotations

from typing import Any, List, Tuple
import sqlite3

_ICON = {"BTC": "🟡", "ETH": "🔷", "SOL": "🟣"}


def _tok(asset: str, side: str) -> str:
    a = (asset or "").upper()
    s = (side or "").lower()
    suffix = "L" if s in {"l", "long", "buy", "bull", "1", "true"} else "S"
    icon = _ICON.get(a, "•")
    return f"{icon} {a}-{suffix}"


def _try_query(conn: sqlite3.Connection, sql: str) -> List[Tuple[str, str]]:
    try:
        cur = conn.cursor()
    except Exception:
        return []
    try:
        cur.execute(sql)
        rows = cur.fetchall()
    except Exception:
        return []
    finally:
        try:
            cur.close()
        except Exception:
            pass

    results: List[Tuple[str, str]] = []
    for row in rows:
        asset = str(row[0]) if len(row) > 0 else ""
        side = str(row[1]) if len(row) > 1 else ""
        results.append((asset, side))
    return results


def compute_positions_icon_line(conn: Any) -> str | None:
    """Return a compact iconified positions line if data is available."""

    if conn is None:
        return None

    candidates = [
        "SELECT asset_symbol, side FROM positions WHERE is_open=1",
        "SELECT asset, side FROM jupiter_positions WHERE is_open=1",
        "SELECT asset, side FROM positions_current WHERE is_open=1",
    ]
    items: List[str] = []
    for sql in candidates:
        rows = _try_query(conn, sql)
        if rows:
            items = [_tok(asset, side) for asset, side in rows]
            break
    if not items:
        return None

    items.sort()
    seen: set[str] = set()
    deduped: List[str] = []
    for token in items:
        if token not in seen:
            deduped.append(token)
            seen.add(token)
    return ", ".join(deduped)
