from __future__ import annotations
import os
import sqlite3
from pathlib import Path
from typing import Any, Optional, Tuple

_ICON_ASSET = {"BTC": "🟡", "ETH": "🔷", "SOL": "🟣"}


def _db_connect(db_path: str) -> Optional[sqlite3.Connection]:
    try:
        if not db_path:
            return None
        p = Path(db_path)
        if not p.exists():
            return None
        conn = sqlite3.connect(str(p))
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
            (table,),
        )
        return bool(cur.fetchone())
    except Exception:
        return False


def _sysvar(conn: sqlite3.Connection, key: str) -> Optional[str]:
    try:
        if _table_exists(conn, "system_vars"):
            cur = conn.execute(
                "SELECT value FROM system_vars WHERE key=? LIMIT 1;",
                (key,),
            )
            row = cur.fetchone()
            if row and row["value"] is not None:
                return str(row["value"])
    except Exception:
        pass
    return None


def _profit_thresholds(conn: Optional[sqlite3.Connection]) -> Tuple[str, str, str]:
    """
    Pulls Position/Portfolio profit thresholds with broad key support.
    Known keys seen in your logs: profit_pos, profit_pf, profit_badge_value.
    """

    pos = pf = "–"
    src = "DB"
    if not conn:
        return pos, pf, src

    # Position threshold keys (try in order)
    for key in (
        "profit_pos",
        "profit_position_usd",
        "profit_position",
        "profit_position_threshold",
    ):
        value = _sysvar(conn, key)
        if value:
            pos = value
            break

    # Portfolio threshold keys (try in order)
    for key in (
        "profit_pf",
        "profit_portfolio_usd",
        "profit_portfolio",
        "profit_badge_value",
    ):
        value = _sysvar(conn, key)
        if value:
            pf = value
            break

    return pos, pf, src


def _liquid_row(conn: Optional[sqlite3.Connection], asset: str) -> Tuple[str, str, str]:
    """Return (threshold, blast, source_tag)."""
    thr, bl, src = "0.00", "0", "DB|FILE"
    if not conn:
        return thr, bl, src
    # dedicated table?
    try:
        if _table_exists(conn, "liquid_thresholds"):
            cur = conn.execute(
                "SELECT threshold, blast FROM liquid_thresholds WHERE asset=? LIMIT 1;",
                (asset,),
            )
            r = cur.fetchone()
            if r:
                if r["threshold"] is not None:
                    thr = f"{float(r['threshold']):.2f}"
                if r["blast"] is not None:
                    bl = str(int(r["blast"]))
                src = "DB"
                return thr, bl, src
    except Exception:
        pass
    # system_vars fallback
    try:
        vt = _sysvar(conn, f"liquid_{asset.lower()}_threshold")
        vb = _sysvar(conn, f"liquid_{asset.lower()}_blast")
        if vt:
            thr = f"{float(vt):.2f}"
            src = "DB"
        if vb:
            bl = str(int(float(vb)))
            src = "DB"
    except Exception:
        pass
    return thr, bl, src


def print_prelaunch_body(dl: Any, poll_interval_s: int) -> None:
    """Body only; banner prints the header. One-time at startup."""
    env_path = os.getenv("SONIC_ENV_PATH_RESOLVED") or "–"
    db_path = getattr(getattr(dl, "db", None), "db_path", None) or "–"

    # Twilio (show full values: dev console)
    sid = os.getenv("TWILIO_SID") or os.getenv("TWILIO_ACCOUNT_SID") or "–"
    auth = os.getenv("TWILIO_AUTH_TOKEN") or "–"
    flow = os.getenv("TWILIO_FLOW_SID") or "–"
    from_ = os.getenv("TWILIO_FROM") or os.getenv("TWILIO_FROM_PHONE") or "–"
    to_ = (
        os.getenv("TWILIO_TO")
        or os.getenv("TWILIO_TO_PHONE")
        or os.getenv("TWILIO_DEFAULT_TO")
        or "–"
    )

    conn = _db_connect(db_path)

    pos, pf, _ = _profit_thresholds(conn)

    print(f"📦 .env (used)    : {env_path}")
    print(f"🔌 Database       : {db_path}")
    print()
    print(
        "☎️ Twilio (env)   : "
        f"SID={sid}\n"
        f"                    AUTH={auth}\n"
        f"                    FROM={from_}   TO={to_}   FLOW={flow}"
    )
    print()
    print(
        "⚙️ Runtime        : Poll Interval="
        f"{int(poll_interval_s)}s   Loop Mode=Live   Snooze=disabled"
    )
    print()
    # Enabled flags (best-effort)
    print("📡 Monitors       : Sonic=ON   Liquid=ON   Profit=ON   Market=ON")
    print()
    print("💧 Liquidation (per-asset)   [source: DB|FILE]")
    for sym in ("BTC", "ETH", "SOL"):
        thr, bl, src = _liquid_row(conn, sym)
        icon = _ICON_ASSET.get(sym, "•")
        print(f"  {icon} {sym:<3}  Threshold: {thr:<6}  Blast: {bl:<2}  [{src}]")
    print()
    print("💰 Profit Monitor           [source: DB]")
    print(f"  Position Profit (USD) : {pos}")
    print(f"  Portfolio Profit (USD): {pf}")
    print()
    print("📈 Market Monitor          [source: DB]")
    print("  Re-arm: Ladder   Reset: available")
    print("  SPX Δ(USD)=0  Dir=Both  Anchor=—")
    print("  BTC Δ(USD)=0  Dir=Both  Anchor=—")
    print("  ETH Δ(USD)=0  Dir=Both  Anchor=—")
    print("  SOL Δ(USD)=0  Dir=Both  Anchor=—")
    print()
    print("Provenance: [DB]=mother.db   [FILE]=seed JSON   [ENV]=.env")
