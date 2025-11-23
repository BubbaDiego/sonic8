from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, List, Optional, Tuple

from backend.data.data_locker import DataLocker
from backend.data.dl_sessions import DLSessions
from .session_models import Session, SessionPerformance, SessionStatus


class SessionCore:
    """
    High-level session services for Sonic.

    All session CRUD and performance queries should go through this class.
    """

    # Table we use for equity/time series
    EQUITY_TABLE = "positions_totals_history"

    def __init__(self, dl: DataLocker) -> None:
        self._dl = dl
        self._store = DLSessions(dl)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _session_window(session: Session) -> Tuple[datetime, datetime]:
        """
        Compute the [start, end] window for a session.

        - Start = created_at
        - End   = closed_at (if closed) or now (UTC)
        """
        start = session.created_at
        if not isinstance(start, datetime):
            start = datetime.fromisoformat(str(start))

        end = session.closed_at or datetime.utcnow()
        if not isinstance(end, datetime):
            end = datetime.fromisoformat(str(end))

        if end < start:
            end = start

        return start, end

    def _get_sqlite_connection(self) -> Any:
        """
        Extract an underlying sqlite3.Connection from DataLocker.

        On Sonic8, DataLocker.db typically returns a DatabaseManager, not the raw
        connection. We duck-type here to support both:
        - Raw connection (has .execute)
        - Manager with .conn or .connection
        """
        db_obj = getattr(self._dl, "db", None)
        if db_obj is None:
            raise RuntimeError("DataLocker.db is None")

        # Raw connection
        if hasattr(db_obj, "execute"):
            return db_obj

        # Manager with .conn or .connection
        for attr in ("conn", "connection"):
            conn = getattr(db_obj, attr, None)
            if conn is not None and hasattr(conn, "execute"):
                return conn

        raise RuntimeError(
            f"Unsupported DataLocker.db type {type(db_obj)!r}: "
            "does not expose a usable sqlite connection"
        )

    def _detect_columns(self, conn: Any, table: str) -> Tuple[str, str, Optional[str]]:
        """
        Inspect the given table and pick:

        - time_col: timestamp-like column
        - value_col: equity / total value column
        - wallet_col: wallet identifier column (optional)

        Raises a RuntimeError with the actual column list if it can't find
        time or value columns.
        """
        cursor = conn.execute(f"PRAGMA table_info({table})")
        rows = cursor.fetchall()
        cols = [row[1] for row in rows]  # row[1] is 'name'
        col_set = set(cols)

        time_candidates = ["timestamp", "snapshot_time", "created_at", "ts"]
        value_candidates = [
            "total_value_usd",
            "total_value",
            "equity_usd",
            "portfolio_value",
            "portfolio_value_usd",
        ]
        wallet_candidates = ["wallet_name", "wallet", "trader_name", "account_name"]

        time_col = None
        for name in time_candidates:
            if name in col_set:
                time_col = name
                break

        value_col = None
        for name in value_candidates:
            if name in col_set:
                value_col = name
                break

        wallet_col = None
        for name in wallet_candidates:
            if name in col_set:
                wallet_col = name
                break

        if time_col is None or value_col is None:
            raise RuntimeError(
                f"{table} does not have a known time/value column. "
                f"Columns={cols}; expected time in {time_candidates}, "
                f"value in {value_candidates}."
            )

        return time_col, value_col, wallet_col

    def _fetch_equity_series(
        self,
        *,
        wallet_name: str,
        start: datetime,
        end: datetime,
    ) -> List[Tuple[datetime, float]]:
        """
        Fetch (timestamp, equity) samples from positions_totals_history (or whichever
        table EQUITY_TABLE names) for the given wallet over the [start, end] window.

        If the table does not have a wallet column, we compute series for all wallets
        combined.
        """
        conn = self._get_sqlite_connection()
        table = self.EQUITY_TABLE

        time_col, value_col, wallet_col = self._detect_columns(conn, table)

        # Dynamically build WHERE clause + params based on whether we have a wallet column
        where_clauses = [f"{time_col} >= ?", f"{time_col} <= ?"]
        params: List[Any] = [start.isoformat(), end.isoformat()]

        if wallet_col is not None:
            where_clauses.insert(0, f"{wallet_col} = ?")
            params.insert(0, wallet_name)

        where_sql = " AND ".join(where_clauses)

        sql = f"""
            SELECT {time_col}, {value_col}
            FROM {table}
            WHERE {where_sql}
            ORDER BY {time_col} ASC
        """

        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()

        series: List[Tuple[datetime, float]] = []

        for row in rows:
            # sqlite3.Row behaves like a sequence; index 0,1 are our columns
            ts_raw, value_raw = row[0], row[1]

            try:
                ts = datetime.fromisoformat(str(ts_raw))
            except Exception:
                continue

            try:
                value = float(value_raw)
            except (TypeError, ValueError):
                continue

            series.append((ts, value))

        return series

    # ------------------------------------------------------------------ #
    # Listing / lookup                                                   #
    # ------------------------------------------------------------------ #

    def list_sessions(self, active_only: bool = False, enabled_only: bool = False) -> List[Session]:
        return self._store.list_sessions(active_only=active_only, enabled_only=enabled_only)

    def list_active_sessions(self) -> List[Session]:
        return self._store.list_sessions(active_only=True)

    def get_session(self, sid: str) -> Optional[Session]:
        return self._store.get_session_by_sid(sid)

    # ------------------------------------------------------------------ #
    # CRUD                                                               #
    # ------------------------------------------------------------------ #

    def create_session(
        self,
        *,
        primary_wallet_name: str,
        name: Optional[str] = None,
        goal: Optional[str] = None,
        tags: Optional[List[str]] = None,
        notes: str = "",
    ) -> Session:
        sid = uuid.uuid4().hex[:8]
        now = datetime.utcnow()
        session = Session(
            sid=sid,
            name=name or f"{primary_wallet_name}-{sid}",
            primary_wallet_name=primary_wallet_name,
            status=SessionStatus.ACTIVE,
            goal=goal,
            tags=tags or [],
            notes=notes or "",
            enabled=True,
            created_at=now,
            updated_at=now,
        )
        return self._store.upsert_session(session)

    def update_session(
        self,
        sid: str,
        *,
        name: Optional[str] = None,
        goal: Optional[str] = None,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
        status: Optional[SessionStatus] = None,
    ) -> Optional[Session]:
        session = self._store.get_session(sid)
        if not session:
            return None

        changed = False

        if name is not None and name != session.name:
            session.name = name
            changed = True

        if goal is not None and goal != session.goal:
            session.goal = goal
            changed = True

        if tags is not None and tags != session.tags:
            session.tags = tags
            changed = True

        if notes is not None and notes != session.notes:
            session.notes = notes
            changed = True

        if status is not None and status != session.status:
            session.status = status
            if status is SessionStatus.CLOSED and session.closed_at is None:
                session.closed_at = datetime.utcnow()
            changed = True

        if not changed:
            return session

        session.touch()
        return self._store.upsert_session(session)

    def close_session(self, sid: str) -> Optional[Session]:
        return self.update_session(sid, status=SessionStatus.CLOSED)

    def delete_session(self, sid: str) -> bool:
        return self._store.delete_session(sid)

    def rename_session(self, sid: str, new_name: str) -> Optional[Session]:
        return self.update_session(sid, name=new_name)

    def set_session_enabled(self, sid: str, enabled: bool) -> Optional[Session]:
        return self._store.set_enabled(sid, enabled)

    # ------------------------------------------------------------------ #
    # Performance API                                                    #
    # ------------------------------------------------------------------ #

    def get_performance(self, sid: str) -> SessionPerformance:
        """
        Compute performance metrics for a given session ID.

        Uses positions_totals_history equity snapshots for the session's primary wallet
        between session.created_at and session.closed_at (or now, if active).
        """
        session = self._store.get_session_by_sid(sid)
        if not session:
            raise RuntimeError(f"Session not found for sid={sid!r}")

        start, end = self._session_window(session)

        series = self._fetch_equity_series(
            wallet_name=session.primary_wallet_name,
            start=start,
            end=end,
        )

        if not series:
            raise RuntimeError(f"No equity samples found for session {sid}")

        # Basic stats
        series_sorted = sorted(series, key=lambda t: t[0])
        first_ts, first_val = series_sorted[0]
        last_ts, last_val = series_sorted[-1]

        pnl = last_val - first_val
        if first_val > 0:
            return_pct: Optional[float] = (pnl / first_val) * 100.0
        else:
            return_pct = None

        # Max drawdown: largest peak-to-trough drop in %
        peak = first_val
        max_dd = 0.0
        for _, value in series_sorted:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak if peak > 0 else 0.0
            if drawdown > max_dd:
                max_dd = drawdown

        max_drawdown_pct = max_dd * 100.0

        return SessionPerformance(
            sid=session.sid,
            name=session.name,
            primary_wallet_name=session.primary_wallet_name,
            start=first_ts,
            end=last_ts,
            start_equity=first_val,
            end_equity=last_val,
            pnl=pnl,
            return_pct=return_pct,
            max_drawdown_pct=max_drawdown_pct,
            samples=len(series_sorted),
        )

    def get_session_performance(self, sid: str) -> Optional[SessionPerformance]:
        try:
            return self.get_performance(sid)
        except RuntimeError:
            return None

    def safe_get_performance(self, sid: str) -> Optional[SessionPerformance]:
        try:
            return self.get_performance(sid)
        except RuntimeError:
            return None
