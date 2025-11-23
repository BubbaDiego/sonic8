from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from backend.data.data_locker import DataLocker
from backend.data.dl_sessions import DLSessions
from .session_models import Session, SessionPerformance, SessionStatus


class SessionCore:
    """
    High-level session services for Sonic.

    All session CRUD should go through this class.
    """

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
            # Defensive: allow raw string fallback
            start = datetime.fromisoformat(str(start))

        end = session.closed_at or datetime.utcnow()
        if not isinstance(end, datetime):
            end = datetime.fromisoformat(str(end))

        # Avoid inverted windows
        if end < start:
            end = start

        return start, end

    def _fetch_equity_series(
        self,
        *,
        wallet_name: str,
        start: datetime,
        end: datetime,
    ) -> List[Tuple[datetime, float]]:
        """
        Fetch (timestamp, equity) samples from monitor_ledger for the given wallet
        over the [start, end] window.

        Assumptions about `monitor_ledger` table (adjust SQL if schema differs):

            - `timestamp`       TEXT  (ISO-8601 string)
            - `wallet_name`     TEXT
            - `portfolio_value` REAL  (total equity / portfolio value for that wallet)

        Returns a list sorted by timestamp ascending.
        """
        conn = self._dl.db  # sqlite3.Connection (see DataLocker)
        conn.row_factory = getattr(conn, "row_factory", None) or None

        # If DataLocker already sets row_factory to sqlite3.Row, we can use dict(row)
        # Otherwise, treat rows as tuples: (timestamp, portfolio_value)
        cursor = conn.execute(
            """
            SELECT timestamp, portfolio_value
            FROM monitor_ledger
            WHERE wallet_name = ?
              AND timestamp >= ?
              AND timestamp <= ?
            ORDER BY timestamp ASC
            """,
            (wallet_name, start.isoformat(), end.isoformat()),
        )

        series: List[Tuple[datetime, float]] = []
        for row in cursor.fetchall():
            if isinstance(row, dict):
                ts_raw = row["timestamp"]
                value_raw = row["portfolio_value"]
            else:
                # sqlite3.Row behaves like a tuple by default; index 0,1 are our columns
                ts_raw, value_raw = row[0], row[1]

            try:
                ts = datetime.fromisoformat(str(ts_raw))
            except Exception:
                # Skip malformed timestamps
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

    def list_sessions(self) -> List[Session]:
        return self._store.list_sessions()

    def list_active_sessions(self) -> List[Session]:
        return [s for s in self._store.list_sessions() if s.status is SessionStatus.ACTIVE]

    def get_session(self, sid: str) -> Optional[Session]:
        return self._store.get_session(sid)

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
        notes: Optional[str] = None,
    ) -> Session:
        sid = uuid.uuid4().hex[:8]
        session = Session(
            sid=sid,
            name=name or f"{primary_wallet_name}-{sid}",
            primary_wallet_name=primary_wallet_name,
            goal=goal,
            tags=tags or [],
            notes=notes,
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

    # ------------------------------------------------------------------ #
    # Performance API                                                    #
    # ------------------------------------------------------------------ #

    def get_session_performance(self, sid: str) -> Optional[SessionPerformance]:
        """
        Compute performance metrics for a given session ID.

        Uses monitor_ledger equity snapshots for the session's primary wallet
        between session.created_at and session.closed_at (or now, if active).
        """
        session = self._store.get_session(sid)
        if not session:
            return None

        start, end = self._session_window(session)

        series = self._fetch_equity_series(
            wallet_name=session.primary_wallet_name,
            start=start,
            end=end,
        )

        if not series:
            # No data; return a "blank" performance object.
            return SessionPerformance(
                sid=session.sid,
                name=session.name,
                primary_wallet_name=session.primary_wallet_name,
                start=start,
                end=end,
                start_equity=None,
                end_equity=None,
                pnl=None,
                return_pct=None,
                max_drawdown_pct=None,
                samples=0,
            )

        # Basic stats
        series_sorted = sorted(series, key=lambda t: t[0])
        first_ts, first_val = series_sorted[0]
        last_ts, last_val = series_sorted[-1]

        pnl = last_val - first_val
        return_pct: Optional[float]
        if first_val > 0:
            return_pct = (pnl / first_val) * 100.0
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
