from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get("SONIC_DB_PATH", ROOT / "backend" / "mother.db"))


def find_table(cur, candidates):
    have = {row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for cand in candidates:
        if cand in have:
            return cand
    return None


def cols(cur, table):
    return [row[1] for row in cur.execute(f"PRAGMA table_info({table})")]


def pick(names, prefs):
    for pref in prefs:
        if pref in names:
            return pref
    return None


def main() -> int:
    con = sqlite3.connect(str(DB))
    cur = con.cursor()

    table = find_table(cur, ["system_vars", "dl_system_data", "dl_system_vars", "dl_system_kv"])
    if not table:
        print("no system vars table")
        return 2

    names = cols(cur, table)
    key_col = pick(names, ["key", "name"])
    val_col = pick(names, ["value", "json", "data", "val", "payload", "content"])
    if not (key_col and val_col):
        print("cannot detect key/value cols:", names)
        return 3

    cfg = {
        "pos": 10,
        "pf": 50,
        "notifications": {"system": True, "voice": False, "sms": False, "tts": False},
    }

    payload = json.dumps(cfg)
    try:
        cur.execute(
            f"INSERT INTO {table}({key_col},{val_col}) VALUES(?,?) ON CONFLICT({key_col}) DO UPDATE SET {val_col}=excluded.{val_col}",
            ("profit_monitor", payload),
        )
    except sqlite3.OperationalError:
        cur.execute(
            f"REPLACE INTO {table}({key_col},{val_col}) VALUES(?,?)",
            ("profit_monitor", payload),
        )

    try:
        cur.execute(f"DELETE FROM {table} WHERE {key_col} IN ('profit_pos','profit_pf')")
    except sqlite3.OperationalError:
        pass

    con.commit()
    con.close()
    print("profit_monitor pos=10 pf=50 voice=False; removed profit_pos/profit_pf")
    return 0


if __name__ == "__main__":
    sys.exit(main())
