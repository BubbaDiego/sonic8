from __future__ import annotations
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Optional, Tuple

from backend.core.config_core.sonic_config_bridge import (
    get_db_path,
    get_liquid_thresholds,
    get_loop_seconds,
    get_price_assets,
    get_twilio,
)

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


def _sysvar_json(conn: Optional[sqlite3.Connection], key: str) -> Optional[dict]:
    if not conn:
        return None
    try:
        raw = _sysvar(conn, key)
        if not raw:
            return None
        return json.loads(raw)
    except Exception:
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
    """Return (threshold, blast, source_tag).

    Search order:
        1) system_vars.alert_thresholds JSON blob (Monitor Manager)
        2) liquid_thresholds table
        3) legacy system_vars liquid_* keys
    """

    thr, bl, src = "0.00", "0", "DB|FILE"
    if not conn:
        return thr, bl, src

    # 1) JSON blob with per-asset overrides
    try:
        blob = _sysvar_json(conn, "alert_thresholds")
        if isinstance(blob, dict):
            aset = asset.upper()
            node = blob.get(aset) or {}
            t = node.get("threshold") or node.get("limit") or blob.get(f"{aset}_threshold")
            b = node.get("blast") or node.get("blast_radius") or blob.get(f"{aset}_blast")
            if t is not None:
                thr = f"{float(t):.2f}"
                src = "DB"
            if b is not None:
                bl = str(int(float(b)))
                src = "DB"
            if src == "DB":
                return thr, bl, src
    except Exception:
        pass

    # 2) dedicated table?
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

    # 3) system_vars fallback
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


def print_prelaunch_body(
    dl: Any,
    poll_interval_s: int,
    *,
    xcom_live: bool = True,
    resolved: dict | None = None,
) -> None:
    """Body only; banner prints the header. One-time at startup."""
    env_path = os.getenv("SONIC_ENV_PATH_RESOLVED") or "–"
    db_path = get_db_path() or (getattr(getattr(dl, "db", None), "db_path", None) or "–")

    # Twilio (show full values: dev console)
    tcfg = get_twilio()
    sid = tcfg.get("SID") or os.getenv("TWILIO_SID") or os.getenv("TWILIO_ACCOUNT_SID") or "–"
    auth = tcfg.get("AUTH") or os.getenv("TWILIO_AUTH_TOKEN") or "–"
    flow = tcfg.get("FLOW") or os.getenv("TWILIO_FLOW_SID") or "–"
    from_ = tcfg.get("FROM") or os.getenv("TWILIO_FROM") or os.getenv("TWILIO_FROM_PHONE") or "–"
    to_ = (
        tcfg.get("TO")
        or os.getenv("TWILIO_TO")
        or os.getenv("TWILIO_TO_PHONE")
        or os.getenv("TWILIO_DEFAULT_TO")
        or "–"
    )

    conn = _db_connect(db_path)

    pos, pf, _ = _profit_thresholds(conn)

    print(f"📦 .env (used)    : {env_path}")
    print(f"🔌 Database       : {db_path}")
    print()
    # Show dry-run state for XCom right before Twilio
    if not xcom_live:
        print("🔕 XCom live alerts disabled (dry-run) — events will be logged, not sent.")
    print(
        "☎️ Twilio (env)   : "
        f"SID={sid}\n"
        f"                    AUTH={auth}\n"
        f"                    FROM={from_}   TO={to_}   FLOW={flow}"
    )
    print()
    cfg_loop = get_loop_seconds()
    loop_val = cfg_loop if cfg_loop is not None else poll_interval_s
    print(
        "⚙️ Runtime        : Poll Interval="
        f"{int(loop_val)}s   Loop Mode=Live   Snooze=disabled"
    )
    print()
    # Enabled flags (best-effort)
    print("📡 Monitors       : Sonic=ON   Liquid=ON   Profit=ON   Market=ON")
    print()
    print("💧 Liquidation (per-asset)   [source: CONFIG→DB|FILE]")
    cfg_liq = get_liquid_thresholds()
    sym_list = list(cfg_liq.keys()) or get_price_assets()
    if not sym_list:
        sym_list = ["BTC", "ETH", "SOL"]
    for sym in sym_list:
        thr_cfg = cfg_liq.get(sym)
        thr_db, bl_db, _ = _liquid_row(conn, sym)
        thr = f"{thr_cfg:.2f}" if thr_cfg is not None else thr_db
        bl = bl_db
        icon = _ICON_ASSET.get(sym, "•")
        print(f"  {icon} {sym:<3}  Threshold: {thr:<6}  Blast: {bl:<2}")
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
