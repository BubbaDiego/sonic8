from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple, List

# Default windows in hours for trend calculation
DEFAULT_WINDOWS: Sequence[Tuple[str, float]] = (
    ("1h", 1.0),
    ("6h", 6.0),
    ("12h", 12.0),
)


# ─────────────────────────────── small helpers ────────────────────────────────

def _to_float(v: Any) -> Optional[float]:
    if v in (None, ""):
        return None
    try:
        return float(v)
    except Exception:
        return None


def _to_utc_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)

    if isinstance(value, str):
        s = value.strip()
        try:
            if s.endswith("Z"):
                return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(
                    timezone.utc
                )
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None

    return None


def _resolve_cursor(dl_or_ctx: Any):
    """
    Try very hard to get a SQLite cursor from whatever you hand us:
    - DataLocker instance
    - {'dl': DataLocker}
    - object with .db.get_cursor()
    - fallback: DataLocker.get_instance()
    """
    candidates: List[Any] = []

    if isinstance(dl_or_ctx, dict):
        for key in ("dl", "data_locker", "locker"):
            cand = dl_or_ctx.get(key)
            if cand is not None:
                candidates.append(cand)
    elif dl_or_ctx is not None:
        candidates.append(dl_or_ctx)

    # Direct candidates
    for src in candidates:
        if not src:
            continue

        # 1) direct get_cursor
        fn = getattr(src, "get_cursor", None)
        if callable(fn):
            try:
                cur = fn()
                if cur:
                    return cur
            except Exception:
                pass

        # 2) db.get_cursor / db.cursor
        db = getattr(src, "db", None)
        if db:
            db_fn = getattr(db, "get_cursor", None)
            if callable(db_fn):
                try:
                    cur = db_fn()
                    if cur:
                        return cur
                except Exception:
                    pass

            cursor_attr = getattr(db, "cursor", None)
            if callable(cursor_attr):
                try:
                    cur = cursor_attr()
                    if cur:
                        return cur
                except Exception:
                    pass

    # 3) Fallback to global DataLocker singleton
    try:
        from backend.data.data_locker import DataLocker  # type: ignore

        dl = DataLocker.get_instance()
        if dl and getattr(dl, "db", None):
            cur = dl.db.get_cursor()
            if cur:
                return cur
    except Exception:
        pass

    return None


def _get_price_at(cursor, asset: str, ts: datetime) -> Optional[float]:
    """
    Look up the price for ``asset`` at or before ``ts`` using the prices table
    populated by PriceMonitor.
    """
    try:
        cutoff = ts.timestamp()
    except Exception:
        return None

    try:
        cursor.execute(
            """
            SELECT current_price, previous_price
            FROM prices
            WHERE asset_type = ? AND CAST(last_update_time AS REAL) <= ?
            ORDER BY CAST(last_update_time AS REAL) DESC
            LIMIT 1
            """,
            (asset, cutoff),
        )
        row = cursor.fetchone()
        if not row:
            return None

        cp = _to_float(row["current_price"])
        pp = _to_float(row["previous_price"])
        return cp if cp is not None else pp
    except Exception:
        return None


# ─────────────────────────── public entrypoint ────────────────────────────────

def compute_price_trends(
    dl_or_ctx: Any,
    anchors: Sequence[Mapping[str, Any]],
    *,
    windows: Sequence[Tuple[str, float]] = DEFAULT_WINDOWS,
) -> Dict[str, Dict[str, Optional[float]]]:
    """
    Compute % move for each asset over the given windows.

    Args:
        dl_or_ctx: DataLocker instance or context dict containing ``dl``.
        anchors: rows that at least expose ``symbol`` (or ``asset_type``),
                 ``price`` (or ``current_price``) and ``ts`` / ``last_update_time``.
        windows: sequence of (label, hours) tuples, e.g. [("1h", 1), ("6h", 6)].

    Returns:
        dict[symbol][window_label] = pct_move (float) or None if insufficient data.
    """
    cursor = _resolve_cursor(dl_or_ctx)
    if cursor is None:
        return {}

    out: Dict[str, Dict[str, Optional[float]]] = {}

    for row in anchors:
        try:
            sym = str(
                row.get("symbol")
                or row.get("asset_type")
                or row.get("asset")
                or ""
            ).upper()
        except Exception:
            continue

        if not sym:
            continue

        cur_price = _to_float(row.get("price") or row.get("current_price"))
        if cur_price is None:
            continue

        ts_raw = row.get("ts") or row.get("last_update_time")
        ts = _to_utc_datetime(ts_raw)
        if ts is None:
            continue

        sym_trends: Dict[str, Optional[float]] = {}
        for label, hours in windows:
            past_ts = ts - timedelta(hours=float(hours))
            prev_price = _get_price_at(cursor, sym, past_ts)
            if prev_price is None or prev_price == 0:
                pct_move: Optional[float] = None
            else:
                pct_move = (cur_price - prev_price) / prev_price * 100.0
            sym_trends[label] = pct_move

        if sym_trends:
            out[sym] = sym_trends

    return out
