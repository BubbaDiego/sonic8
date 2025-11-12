from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import json


def _get_mgr(dl: Any):
    return getattr(dl, "dl_monitors", None) or getattr(dl, "monitors", None)


def _rows_in_mgr(mgr: Any) -> List[Dict[str, Any]]:
    if not mgr:
        return []
    for meth in ("get_rows", "latest", "list", "all"):
        fn = getattr(mgr, meth, None)
        if callable(fn):
            try:
                got = fn()
                return got if isinstance(got, list) else []
            except Exception:
                continue
    arr = getattr(mgr, "rows", None) or getattr(mgr, "items", None)
    return list(arr) if isinstance(arr, list) else []


def _replace_mgr(mgr: Any, rows: List[Dict[str, Any]]) -> None:
    if not mgr:
        return
    for meth in ("replace", "set_rows", "reset", "load", "update_rows"):
        fn = getattr(mgr, meth, None)
        if callable(fn):
            fn(rows)
            return
    try:
        setattr(mgr, "rows", list(rows))
    except Exception:
        pass


def _latest_cycle_id(cur) -> Optional[str]:
    for t in ("monitor_status", "monitor_statuses", "monitor_status_log"):
        try:
            cur.execute(f"SELECT MAX(cast(cycle_id as TEXT)) FROM {t}")
            row = cur.fetchone()
            if row and row[0]:
                return str(row[0])
        except Exception:
            continue
    return None


def _rows_from_status_tables(dl: Any) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    db = getattr(dl, "db", None)
    if not db or not hasattr(db, "get_cursor"):
        return [], None
    cur = db.get_cursor()
    cid = _latest_cycle_id(cur)
    if not cid:
        return [], None
    rows: List[Dict[str, Any]] = []
    for t in ("monitor_status", "monitor_statuses", "monitor_status_log"):
        try:
            cur.execute(
                f"""
                SELECT monitor, COALESCE(label, monitor), state, value,
                       COALESCE(unit,''), COALESCE(thr_op,NULL),
                       COALESCE(thr_value,NULL), COALESCE(thr_unit,''),
                       COALESCE(ts,NULL), COALESCE(source,''), COALESCE(meta,NULL)
                FROM {t}
                WHERE cast(cycle_id as TEXT) = ?
                ORDER BY id ASC
            """,
                (cid,),
            )
            for (
                monitor,
                label,
                state,
                value,
                unit,
                thr_op,
                thr_value,
                thr_unit,
                ts,
                source,
                meta,
            ) in cur.fetchall():
                meta_dict = {}
                if isinstance(meta, str):
                    try:
                        meta_dict = json.loads(meta)
                    except Exception:
                        meta_dict = {}
                elif isinstance(meta, dict):
                    meta_dict = meta
                rows.append(
                    {
                        "monitor": (monitor or "").lower(),
                        "label": label or monitor or "",
                        "state": (state or "OK").upper(),
                        "value": value,
                        "unit": unit or "",
                        "thr_op": thr_op,
                        "thr_value": thr_value,
                        "thr_unit": thr_unit,
                        "ts": ts,
                        "source": source or (monitor or ""),
                        "meta": meta_dict,
                    }
                )
            if rows:
                break
        except Exception:
            continue
    return rows, cid


def ensure_bus_has_current_cycle(dl: Any, logger) -> int:
    """
    If dl.monitors has no rows but DB has monitor_status for the current cycle,
    backfill in-memory bus and return injected count.
    """
    mgr = _get_mgr(dl)
    if not mgr:
        logger.info("[mon] no dl.monitors manager on DataLocker; cannot publish")
        return 0
    existing = _rows_in_mgr(mgr)
    if existing:
        return len(existing)
    rows, cid = _rows_from_status_tables(dl)
    if rows:
        _replace_mgr(mgr, rows)
        logger.warning(
            "[mon] dl_monitors empty; backfilled %d rows from DB (cycle=%s)",
            len(rows),
            cid,
        )
        return len(rows)
    return 0
