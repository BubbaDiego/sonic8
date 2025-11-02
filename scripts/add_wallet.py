# -*- coding: utf-8 -*-
"""
add_wallet.py — interactive wallet inserter (Name + Public Address)

Run with prompts:
  python scripts/add_wallet.py

Or with flags:
  python scripts/add_wallet.py --name "My Wallet" --address "YourPublicAddressHere"
  # optional: --db "C:/sonic7/backend/mother.db"

Behavior:
- Creates table wallets(...) if absent.
- On duplicate address, updates name + updated_at (upsert).
- Loud, unicode status lines so results are obvious.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

IC_WALLET = "👛"
IC_DB     = "💾"
IC_OK     = "✅"
IC_SKIP   = "⏭"
IC_FAIL   = "❌"
IC_BULLET = "•"
IC_ASK    = "❓"

DEFAULT_DB = os.environ.get("MOTHER_DB_PATH") or r"C:\sonic7\backend\mother.db"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS wallets (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    address    TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT
);
"""

UPSERT_SQL = """
INSERT INTO wallets (name, address)
VALUES (?, ?)
ON CONFLICT(address)
DO UPDATE SET
    name       = excluded.name,
    updated_at = datetime('now');
"""

SELECT_SQL = "SELECT id, name, address, created_at, COALESCE(updated_at,'') FROM wallets WHERE address = ?"


def _resolve_db(path_arg: str | None) -> Path:
    if path_arg:
        return Path(path_arg).expanduser().resolve()
    if DEFAULT_DB:
        return Path(DEFAULT_DB).expanduser().resolve()
    # fallback: repo-root/backend/mother.db relative to this script
    here = Path(__file__).resolve()
    return (here.parent.parent / "backend" / "mother.db").resolve()


def _validate_address(addr: str) -> None:
    s = addr.strip()
    if not s:
        raise ValueError("Address is empty.")
    # light sanity (schema-agnostic)
    if len(s) < 20:
        raise ValueError("Address looks too short (min ~20 chars).")
    if any(c.isspace() for c in s):
        raise ValueError("Address must not contain whitespace.")


def _prompt_nonempty(label: str) -> str:
    while True:
        val = input(f"{IC_ASK} {label}: ").strip()
        if val:
            return val
        print(f"{IC_FAIL} {label} cannot be empty.")


def _prompt_db(default_path: Path) -> Path:
    show = str(default_path)
    ans = input(f"{IC_ASK} Database path [{show}]: ").strip()
    if not ans:
        return default_path
    return Path(ans).expanduser().resolve()


def _confirm(summary: str) -> bool:
    print(summary)
    ans = input(f"{IC_ASK} Proceed? [y/N]: ").strip().lower()
    return ans in ("y", "yes")


def main():
    ap = argparse.ArgumentParser(description="Insert (or update) a wallet record (Name + Public Address).", add_help=True)
    ap.add_argument("--name",    help="Wallet display name (string)")
    ap.add_argument("--address", help="Public address (string)")
    ap.add_argument("--db",      help=f"Path to SQLite DB (default: {DEFAULT_DB})")
    args = ap.parse_args()

    # Interactive prompts if flags missing
    name    = args.name
    address = args.address

    if not name:
        name = _prompt_nonempty("Name")
    if not address:
        address = _prompt_nonempty("Public Address")

    # Resolve & optionally override DB
    db_path = _resolve_db(args.db)
    if not args.db:
        db_path = _prompt_db(db_path)

    # Echo plan
    print(f"\n{IC_WALLET}  Add wallet")
    print(f"  {IC_BULLET} Name   : {name}")
    print(f"  {IC_BULLET} Address: {address}")
    print(f"{IC_DB}  DB     : {db_path}")

    # Validate address
    try:
        _validate_address(address)
    except Exception as e:
        print(f"{IC_FAIL} invalid address → {e}")
        sys.exit(2)

    # Confirm
    if not _confirm(""):
        print(f"{IC_SKIP} canceled")
        sys.exit(130)

    # Do the work
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(db_path)) as cx:
            cx.execute("PRAGMA journal_mode=WAL;")
            cx.execute(CREATE_SQL)
            cx.execute(UPSERT_SQL, (name.strip(), address.strip()))
            cx.commit()

            row = cx.execute(SELECT_SQL, (address.strip(),)).fetchone()
            if row:
                rid, rname, raddr, rcreated, rupdated = row
                status = f"{IC_OK} upserted" if rupdated else f"{IC_OK} inserted"
                print(f"\n{status}  (id={rid})")
                print(f"  {IC_BULLET} Name   : {rname}")
                print(f"  {IC_BULLET} Address: {raddr}")
                print(f"  {IC_BULLET} Created: {rcreated}")
                if rupdated:
                    print(f"  {IC_BULLET} Updated: {rupdated}")
            else:
                print(f"{IC_FAIL} upsert failed (no row returned)")
                sys.exit(1)

    except sqlite3.Error as e:
        print(f"{IC_FAIL} sqlite error → {e}")
        sys.exit(1)
    except Exception as e:
        print(f"{IC_FAIL} unexpected error → {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"{IC_SKIP} canceled by user")
        sys.exit(130)
