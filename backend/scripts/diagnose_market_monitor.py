#!/usr/bin/env python
"""
End‑to‑end diagnostic for the Market‑Monitor %‑move pipeline.

Usage:  python diagnose_market_monitor.py
"""

from datetime import datetime, timedelta, timezone
from pprint import pprint
from textwrap import dedent
from datetime import datetime, timezone, timedelta
from backend.data.data_locker import DataLocker
from backend.core.monitor_core.market_monitor import MarketMonitor

dl  = DataLocker.get_instance()          # uses default DB path
mon = MarketMonitor(dl)
cur = dl.db.get_cursor()

ASSETS  = mon.ASSETS
WINDOWS = mon.WINDOWS                    # {'1h': 3600, '6h': 21600, '24h': 86400}

banner = lambda t: print(f"\n{'='*9} {t} {'='*9}")

# ------------------------------------------------------------------ #
# 1. Show table schema + a couple of rows
# ------------------------------------------------------------------ #
banner("prices schema & sample rows")
cur.execute("PRAGMA table_info(prices)")
cols = [f"{r[1]} ({r[2]})" for r in cur.fetchall()]
print("columns:", ", ".join(cols))
cur.execute("SELECT * FROM prices LIMIT 3")
rows = cur.fetchall()
for r in rows:
    print(dict(r))

# ------------------------------------------------------------------ #
# 2. Row count + oldest/newest per asset
# ------------------------------------------------------------------ #
banner("row count / oldest / newest")
cur.execute("""
    SELECT asset_type,
           COUNT(*)                       AS rows,
           MIN(last_update_time)          AS oldest,
           MAX(last_update_time)          AS newest
    FROM prices
    GROUP BY asset_type
""")
for r in cur.fetchall():
    print(dict(r))

# ------------------------------------------------------------------ #
# 3. Raw _price_at results
# ------------------------------------------------------------------ #
banner("MarketMonitor._price_at() check")
now = datetime.now(timezone.utc).isoformat(timespec="seconds")
print("now =", now)
for a in ASSETS:
    print(f"\n{a}:")
    for label, secs in WINDOWS.items():
        print(f"  {label:>3} ago ->", mon._price_at(a, secs))

# ------------------------------------------------------------------ #
# 4. Manual %‑move calculation
# ------------------------------------------------------------------ #
banner("manual % calculation")
for a in ASSETS:
    cur_p = mon._price_at(a, 0)
    if not cur_p:
        print(f"{a}: no current price")
        continue
    print(f"\n{a}: current = {cur_p}")
    for label, secs in WINDOWS.items():
        prev = mon._price_at(a, secs)
        pct  = None if not prev else (cur_p - prev) / prev * 100
        print(f"  {label:>3}: prev={prev}  pct={pct}")

# ------------------------------------------------------------------ #
# 5. Latest monitor_ledger row
# ------------------------------------------------------------------ #
banner("latest monitor_ledger entry")
cur.execute("""
    SELECT status, created_at, metadata
    FROM   monitor_ledger
    WHERE  monitor_name='market_monitor' AND status='Success'
    ORDER  BY created_at DESC LIMIT 1
""")
row = cur.fetchone()
if row:
    pprint(dict(row))
else:
    print("No ledger rows found for market_monitor")

# ------------------------------------------------------------------ #
# Quick advice
# ------------------------------------------------------------------ #
banner("Actions")
issues = []

# Issue A – no history
cur.execute("SELECT COUNT(*) FROM prices").fetchone()
for a in ASSETS:
    cur.execute("SELECT COUNT(*) FROM prices WHERE asset_type=?", (a,))
    if cur.fetchone()[0] < 3:
        issues.append(f"Not enough history for {a}")

# Issue B – _price_at() always returns latest
bad = []
for a in ASSETS:
    vals = [mon._price_at(a, s) for s in WINDOWS.values()]
    if len(set(vals)) == 1:
        bad.append(a)
if bad:
    issues.append(f"_price_at() gives same price for all windows: {', '.join(bad)}")

if not issues:
    print("✅ All good – you should be seeing non‑zero % moves.")
else:
    for i in issues:
        print("❌", i)
    print("\nNext steps:")
    if any("Not enough history" in i for i in issues):
        print("  • Run your price‑sync service for a few hours *or* use the"
              " bulk back‑fill script (CoinGecko market_chart) to seed history.")
    if any("_price_at()" in i for i in issues):
        print(dedent("""
            • Patch backend/core/monitor_core/market_monitor.py
              Replace the current `_price_at()` with:

                  ts_cut = (datetime.now(timezone.utc)
                            - timedelta(seconds=seconds_ago)).isoformat()
                  …
                  WHERE asset_type=? AND last_update_time<=?
                  ORDER BY last_update_time DESC

              so both sides of the comparison are ISO strings.
        """))
