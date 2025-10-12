from __future__ import annotations

from typing import Iterable, Tuple, List, Any
import sqlite3

_ICON = {"BTC": "🟡", "ETH": "🔷", "SOL": "🟣"}


def _tok(asset: str, side: str) -> str:
    a = (asset or "").upper()
    s = (side or "").lower()
    suffix = "L" if s in {"l", "long", "buy", "bull", "1", "true"} else "S"
    icon = _ICON.get(a, "•")
    return f"{icon} {a}-{suffix}"


def _try_query(conn: sqlite3.Connection, sql: str) -> Iterable[Tuple[str, str]]:
    cur = conn.cursor()
    try:
        cur.execute(sql)
        for row in cur.fetchall():
            a = str(row[0]) if len(row) > 0 else ""
            s = str(row[1]) if len(row) > 1 else ""
            yield (a, s)
    except Exception:
        return []
    finally:
        try:
            cur.close()
        except Exception:
            pass


def compute_positions_icon_line(conn: Any) -> str | None:
    if conn is None:
        return None
    candidates = [
        "SELECT asset_symbol, side FROM positions WHERE is_open=1",
        "SELECT asset, side FROM jupiter_positions WHERE is_open=1",
        "SELECT asset, side FROM positions_current WHERE is_open=1",
    ]
    items: List[str] = []
    for sql in candidates:
        rows = list(_try_query(conn, sql))
        if rows:
            items = [_tok(a, s) for a, s in rows]
            break
    if not items:
        return None
    items = sorted(set(items))
    return ", ".join(items)
