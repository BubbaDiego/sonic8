# dl_portfolio.py
"""
Author: BubbaDiego
Module: DLPortfolioManager
Description:
    Handles recording and retrieving portfolio snapshots including total size,
    value, collateral, and metrics like leverage and heat index over time.

Dependencies:
    - DatabaseManager from database.py
    - ConsoleLogger from console_logger.py
"""

from uuid import uuid4
from datetime import datetime
from typing import List, Optional, Tuple
from backend.core.logging import log
from backend.models.portfolio import PortfolioSnapshot

class DLPortfolioManager:
    def __init__(self, db):
        self.db = db
        log.debug("DLPortfolioManager initialized.", source="DLPortfolioManager")

    def record_snapshot(self, totals: "PortfolioSnapshot | dict"):
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable for portfolio snapshot", source="DLPortfolioManager")
                return

            if isinstance(totals, PortfolioSnapshot):
                if hasattr(totals, "model_dump"):
                    data = totals.model_dump()
                elif hasattr(totals, "dict"):
                    data = totals.dict()
                else:
                    data = totals.__dict__
            else:
                data = dict(totals)

            data.setdefault("id", str(uuid4()))
            if isinstance(data.get("snapshot_time"), datetime):
                data["snapshot_time"] = data["snapshot_time"].isoformat()
            data.setdefault("snapshot_time", datetime.now().isoformat())
            if isinstance(data.get("session_start_time"), datetime):
                data["session_start_time"] = data["session_start_time"].isoformat()

            start = float(data.get("session_start_value") or 0.0)
            total = float(data.get("total_value") or 0.0)
            data["current_session_value"] = total - start

            cursor.execute(
                """
                INSERT INTO positions_totals_history (
                    id, snapshot_time, total_size, total_long_size, total_short_size, total_value,
                    total_collateral, avg_leverage, avg_travel_percent, avg_heat_index,
                    total_heat_index, market_average_sp500,
                    session_start_time, session_start_value, current_session_value,
                    session_goal_value, session_performance_value
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.get("id"),
                    data.get("snapshot_time"),
                    data.get("total_size", 0.0),
                    data.get("total_long_size", 0.0),
                    data.get("total_short_size", 0.0),
                    data.get("total_value", 0.0),
                    data.get("total_collateral", 0.0),
                    data.get("avg_leverage", 0.0),
                    data.get("avg_travel_percent", 0.0),
                    data.get("avg_heat_index", 0.0),
                    data.get("total_heat_index", 0.0),
                    data.get("market_average_sp500", 0.0),
                    data.get("session_start_time"),
                    data.get("session_start_value", 0.0),
                    data["current_session_value"],
                    data.get("session_goal_value", 0.0),
                    data.get("session_performance_value", 0.0),
                ),
            )
            self.db.commit()
            log.success("Portfolio snapshot recorded", source="DLPortfolioManager")
        except Exception as e:
            log.error(f"Failed to record portfolio snapshot: {e}", source="DLPortfolioManager")

    def get_equity_series(
        self,
        *,
        start: datetime,
        end: datetime,
        wallet_name: Optional[str] = None,
    ) -> List[Tuple[datetime, float]]:
        """
        Return a time-ordered list of (timestamp, total_value) snapshots from
        positions_totals_history between [start, end].

        If positions_totals_history has a wallet-identifying column, filter by
        wallet_name when provided; otherwise, use all rows.
        """

        try:
            cursor = self.db.get_cursor()
        except Exception:
            cursor = None

        if cursor is None:
            log.error("DB unavailable while fetching equity series", source="DLPortfolioManager")
            return []

        cursor.execute("PRAGMA table_info(positions_totals_history)")
        cols_raw = cursor.fetchall() or []
        col_names = [row[1] for row in cols_raw]
        col_set = set(col_names)

        time_col = None
        for candidate in ("snapshot_time", "timestamp", "created_at", "ts"):
            if candidate in col_set:
                time_col = candidate
                break

        value_col = None
        for candidate in (
            "total_value",
            "total_value_usd",
            "equity_usd",
            "portfolio_value",
            "portfolio_value_usd",
        ):
            if candidate in col_set:
                value_col = candidate
                break

        wallet_col = None
        for candidate in ("wallet_name", "wallet", "trader_name", "account_name"):
            if candidate in col_set:
                wallet_col = candidate
                break

        if time_col is None or value_col is None:
            log.error(
                "positions_totals_history missing expected columns",
                source="DLPortfolioManager",
            )
            return []

        where_clauses = [f"{time_col} >= ?", f"{time_col} <= ?"]
        params: List[str] = [start.isoformat(), end.isoformat()]

        if wallet_col and wallet_name is not None:
            where_clauses.insert(0, f"{wallet_col} = ?")
            params.insert(0, wallet_name)

        where_sql = " AND ".join(where_clauses)
        cursor.execute(
            f"SELECT {time_col}, {value_col} FROM positions_totals_history "
            f"WHERE {where_sql} ORDER BY {time_col} ASC",
            params,
        )

        series: List[Tuple[datetime, float]] = []
        for ts_raw, value_raw in cursor.fetchall() or []:
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

    def get_snapshots(self) -> list[PortfolioSnapshot]:
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable while fetching snapshots", source="DLPortfolioManager")
                return []
            cursor.execute("SELECT * FROM positions_totals_history ORDER BY snapshot_time ASC")
            rows = cursor.fetchall()
            log.debug(f"Retrieved {len(rows)} portfolio snapshots", source="DLPortfolioManager")
            snapshots = []
            for row in rows:
                data = dict(row)
                for field in [
                    "total_size",
                    "total_long_size",
                    "total_short_size",
                    "total_value",
                    "total_collateral",
                    "avg_leverage",
                    "avg_travel_percent",
                    "avg_heat_index",
                    "total_heat_index",
                    "market_average_sp500",
                    "session_start_value",
                    "current_session_value",
                    "session_goal_value",
                    "session_performance_value",
                ]:
                    if data.get(field) is None:
                        data[field] = 0.0
                snapshots.append(PortfolioSnapshot(**data))
            return snapshots
        except Exception as e:
            log.error(f"Failed to fetch portfolio snapshots: {e}", source="DLPortfolioManager")
            return []

    def get_latest_snapshot(self) -> PortfolioSnapshot | None:
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable while fetching latest snapshot", source="DLPortfolioManager")
                return None
            cursor.execute("SELECT * FROM positions_totals_history ORDER BY snapshot_time DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                log.debug("Latest portfolio snapshot retrieved", source="DLPortfolioManager")
                data = dict(row)
                for field in ["total_size", "total_long_size", "total_short_size", "total_value",
                              "total_collateral", "avg_leverage", "avg_travel_percent",
                              "avg_heat_index", "total_heat_index", "market_average_sp500",
                              "session_start_value", "current_session_value",
                              "session_goal_value", "session_performance_value"]:
                    if data.get(field) is None:
                        data[field] = 0.0

                # Add this conditional logic here
                if data.get("session_start_time") is None:
                    data["session_start_time"] = datetime.now().isoformat()  # fallback to now or appropriate logic

                return PortfolioSnapshot(**data)
            return None
        except Exception as e:
            log.error(f"Failed to fetch latest snapshot: {e}", source="DLPortfolioManager")
            return None

    def add_entry(self, entry: dict):
        """Insert a manual portfolio entry into positions_totals_history."""
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable, cannot add portfolio entry", source="DLPortfolioManager")
                return
            if "id" not in entry:
                entry["id"] = str(uuid4())
            if "snapshot_time" not in entry:
                entry["snapshot_time"] = datetime.now().isoformat()
            if isinstance(entry.get("session_start_time"), datetime):
                entry["session_start_time"] = entry["session_start_time"].isoformat()

            start = float(entry.get("session_start_value") or 0.0)
            total = float(entry.get("total_value") or 0.0)
            entry["current_session_value"] = total - start
            cursor.execute(
                """
                INSERT INTO positions_totals_history (
                    id, snapshot_time, total_size, total_long_size, total_short_size, total_value,
                    total_collateral, avg_leverage, avg_travel_percent, avg_heat_index,
                    total_heat_index, market_average_sp500,
                    session_start_time, session_start_value, current_session_value,
                    session_goal_value, session_performance_value
                ) VALUES (:id, :snapshot_time, :total_size, :total_long_size, :total_short_size, :total_value,
                          :total_collateral, :avg_leverage, :avg_travel_percent, :avg_heat_index,
                          :total_heat_index, :market_average_sp500,
                          :session_start_time, :session_start_value, :current_session_value,
                          :session_goal_value, :session_performance_value)
                """,
                {
                    "id": entry["id"],
                    "snapshot_time": entry.get("snapshot_time"),
                    "total_size": entry.get("total_size", 0.0),
                    "total_long_size": entry.get("total_long_size", 0.0),
                    "total_short_size": entry.get("total_short_size", 0.0),
                    "total_value": entry.get("total_value", 0.0),
                    "total_collateral": entry.get("total_collateral", 0.0),
                    "avg_leverage": entry.get("avg_leverage", 0.0),
                    "avg_travel_percent": entry.get("avg_travel_percent", 0.0),
                    "avg_heat_index": entry.get("avg_heat_index", 0.0),
                    "total_heat_index": entry.get("total_heat_index", 0.0),
                    "market_average_sp500": entry.get("market_average_sp500", 0.0),
                    "session_start_time": entry.get("session_start_time"),
                    "session_start_value": entry.get("session_start_value", 0.0),
                    "current_session_value": entry["current_session_value"],
                    "session_goal_value": entry.get("session_goal_value", 0.0),
                    "session_performance_value": entry.get("session_performance_value", 0.0),
                },
            )
            self.db.commit()
            log.success(f"Portfolio entry added: {entry['id']}", source="DLPortfolioManager")
        except Exception as e:
            log.error(f"Failed to add portfolio entry: {e}", source="DLPortfolioManager")

    def update_entry(self, entry_id: str, fields: dict):
        """Update fields of an existing portfolio entry by id."""
        try:
            if not fields:
                return
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable, cannot update entry", source="DLPortfolioManager")
                return
            recalc_needed = (
                "current_session_value" not in fields
                and ("total_value" in fields or "session_start_value" in fields)
            ) or (
                "session_performance_value" not in fields
                and ("total_value" in fields or "session_start_value" in fields)
            )

            existing = None
            if recalc_needed:
                existing = self.get_entry_by_id(entry_id) or {}
                total = float(fields.get("total_value", existing.get("total_value", 0.0)) or 0.0)
                start = float(fields.get("session_start_value", existing.get("session_start_value", 0.0)) or 0.0)
                delta = total - start
                fields.setdefault("current_session_value", delta)
                fields.setdefault("session_performance_value", delta)
            set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
            params = list(fields.values()) + [entry_id]
            cursor.execute(
                f"UPDATE positions_totals_history SET {set_clause} WHERE id = ?",
                params,
            )
            self.db.commit()
            log.info(f"Portfolio entry updated: {entry_id}", source="DLPortfolioManager")
        except Exception as e:
            log.error(f"Failed to update portfolio entry {entry_id}: {e}", source="DLPortfolioManager")

    def get_entry_by_id(self, entry_id: str) -> dict:
        """Return a portfolio entry by its ID."""
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable while fetching entry", source="DLPortfolioManager")
                return None
            cursor.execute(
                "SELECT * FROM positions_totals_history WHERE id = ?",
                (entry_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            log.error(f"Failed to fetch portfolio entry {entry_id}: {e}", source="DLPortfolioManager")
            return None

    def delete_entry(self, entry_id: str):
        """Delete a portfolio entry by ID."""
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable, cannot delete entry", source="DLPortfolioManager")
                return
            cursor.execute(
                "DELETE FROM positions_totals_history WHERE id = ?",
                (entry_id,),
            )
            self.db.commit()
            log.info(f"Portfolio entry deleted: {entry_id}", source="DLPortfolioManager")
        except Exception as e:
            log.error(f"Failed to delete portfolio entry {entry_id}: {e}", source="DLPortfolioManager")

    def clear_snapshots(self):
        """Remove all portfolio snapshot rows."""
        try:
            cursor = self.db.get_cursor()
            if cursor is None:
                log.error("DB unavailable, cannot clear portfolio history", source="DLPortfolioManager")
                return
            cursor.execute("DELETE FROM positions_totals_history")
            self.db.commit()
            log.success("🧹 Portfolio history cleared", source="DLPortfolioManager")
        except Exception as e:  # pragma: no cover - defensive
            log.error(f"Failed to clear portfolio history: {e}", source="DLPortfolioManager")
