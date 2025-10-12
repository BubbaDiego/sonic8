from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Optional, Tuple

_ICON_ASSET = {"BTC": "🟡", "ETH": "🔷", "SOL": "🟣"}


def _mask(v: Optional[str]) -> str:
    if not v or v == "-":
        return "–"
    return f"{v[:3]}…"


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


def _get_sysvar(conn: sqlite3.Connection, key: str) -> Tuple[Optional[str], str]:
    """Return (value, provenance). Prefer DB, else return (None,'–')."""

    try:
        if _table_exists(conn, "system_vars"):
            cur = conn.execute(
                "SELECT value FROM system_vars WHERE key=? LIMIT 1;",
                (key,),
            )
            row = cur.fetchone()
            if row and row["value"] is not None:
                return (str(row["value"]), "[DB]")
    except Exception:
        pass
    return (None, "–")


def _get_profit_thresholds(conn: Optional[sqlite3.Connection]) -> Tuple[str, str, str]:
    pos, pprov = ("–", "–")
    pf, pfprov = ("–", "–")
    if conn:
        pos, pprov = _get_sysvar(conn, "profit_pos")
        pf, pfprov = _get_sysvar(conn, "profit_pf")
    return (pos or "–", pf or "–", pprov if pprov != "–" else pfprov)


def _get_liquid_per_asset(conn: Optional[sqlite3.Connection], asset: str) -> Tuple[str, str, str]:
    """Return (threshold, blast, provenance_tag)."""

    t, b, prov = ("0.00", "0", "–")
    if not conn:
        return (t, b, prov)
    # try a few likely places
    try:
        if _table_exists(conn, "liquid_thresholds"):
            cur = conn.execute(
                "SELECT threshold, blast FROM liquid_thresholds WHERE asset=? LIMIT 1;",
                (asset,),
            )
            row = cur.fetchone()
            if row:
                t = f"{float(row['threshold']):.2f}" if row["threshold"] is not None else t
                b = str(int(row["blast"])) if row["blast"] is not None else b
                prov = "[DB]"
                return (t, b, prov)
    except Exception:
        pass
    # system_vars fallback
    try:
        key_t = f"liquid_{asset.lower()}_threshold"
        key_b = f"liquid_{asset.lower()}_blast"
        vt, p1 = _get_sysvar(conn, key_t)
        vb, p2 = _get_sysvar(conn, key_b)
        if vt or vb:
            t = f"{float(vt):.2f}" if vt else t
            b = str(int(float(vb))) if vb else b
            prov = p1 if p1 != "–" else p2
            return (t, b, prov or "[DB]")
    except Exception:
        pass
    return (t, b, prov)


def print_prelaunch_checklist(dl: Any, poll_interval_s: int) -> None:
    env_path = os.getenv("SONIC_ENV_PATH_RESOLVED") or "–"
    db_path = getattr(getattr(dl, "db", None), "db_path", None) or "–"

    sid = os.getenv("TWILIO_SID") or os.getenv("TWILIO_ACCOUNT_SID") or "–"
    auth = os.getenv("TWILIO_AUTH_TOKEN")
    from_ = os.getenv("TWILIO_FROM") or os.getenv("TWILIO_FROM_PHONE") or "–"
    to_ = (
        os.getenv("TWILIO_TO")
        or os.getenv("TWILIO_TO_PHONE")
        or os.getenv("TWILIO_DEFAULT_TO")
        or "–"
    )

    conn = _db_connect(db_path)

    # Profit thresholds (best-effort DB read)
    profit_pos, profit_pf, profit_prov = _get_profit_thresholds(conn)

    # Liquid monitor per asset
    rows = []
    for symbol in ("BTC", "ETH", "SOL"):
        thr, blast, prov = _get_liquid_per_asset(conn, symbol)
        icon = _ICON_ASSET.get(symbol, "•")
        rows.append(
            f"    {icon} {symbol:<3} • Threshold: {thr:<6} • Blast: {blast:<2}    "
            f"{'[DB|FILE]' if prov == '–' else prov}"
        )

    print(
        "════════════════════════════════ 🧪 Pre-Launch Checklist (one-time) ════════════════════════════════"
    )
    print(f"📦 .env (used): {env_path}")
    print(f"🔌 Database   : {db_path}")
    print()
    print("  🔐 Twilio config")
    print(
        f"    ☎️ Voice/SMS : sid={_mask(sid)}  auth={'••••' if auth else '–'}  from={from_}  to={to_}    {'[ENV]'}"
    )
    print(
        f"    🔊 TTS       : engine=pyttsx3      {'present' if _has_pyttsx3() else 'missing'}"
    )
    print()
    print("  ⚙️ Sonic Monitor (runtime)")
    print(f"    🕒 Poll Interval : {int(poll_interval_s)}s")
    print()
    print("  💧 Liquidation Monitor")
    for r in rows:
        print(r)
    print()
    print("  💰 Profit Monitor")
    print(f"    Position Profit (USD)  : {profit_pos}    {profit_prov}")
    print(f"    Portfolio Profit (USD) : {profit_pf}     {profit_prov}")
    print()
    print("  🔎 Provenance summary")
    print("    [DB] = mother.db     [FILE] = seeded JSON fallbacks     [ENV] = .env")
    print(
        "════════════════════════════════════════════════════════════════════════════════════════════════════"
    )


def _has_pyttsx3() -> bool:
    try:
        import importlib.util as iu

        return iu.find_spec("pyttsx3") is not None
    except Exception:
        return False
