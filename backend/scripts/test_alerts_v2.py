#!/usr/bin/env python3
"""
Alert V2 Health Check
––––––––––––––––––––––
Verifies that the database schema, seed data, and orchestrator loop
are wired correctly.

• Works with either  `backend.alert_v2`  or  `backend.alert_v2_hybrid`.
• Creates nothing permanent – it rolls back test rows in a savepoint.

Usage:
    python scripts/alert_v2_health_check.py
"""

from __future__ import annotations

import contextlib
import importlib
import sys
from datetime import datetime, timedelta
from uuid import uuid4

import sqlalchemy
from rich.console import Console
from rich.table import Table

console = Console()

# ----------------------------------------------------------------------
# 1. Locate the alert package (hybrid first, fallback to v2 classic)
# ----------------------------------------------------------------------
for mod_name in ("backend.alert_v2_hybrid", "backend.alert_v2"):
    try:
        alert_pkg = importlib.import_module(mod_name)
        console.print(f"[bold green]✓[/] Using package [cyan]{mod_name}[/]")
        break
    except ModuleNotFoundError:
        continue
else:
    console.print("[bold red]✗[/] Neither backend.alert_v2_hybrid nor backend.alert_v2 found.")
    sys.exit(1)

# Typed imports after dynamic load
from sqlalchemy import inspect

AlertRepo = alert_pkg.AlertRepo
models = importlib.import_module(f"{alert_pkg.__name__}.models")
AlertConfig = models.AlertConfig
Condition = models.Condition
Threshold = models.Threshold
AlertLevel = models.AlertLevel

# ----------------------------------------------------------------------
# 2. Open repo + ensure schema exists
# ----------------------------------------------------------------------
repo = AlertRepo()
repo.ensure_schema()
engine = repo.session.get_bind()
insp = inspect(engine)

required_tables = [
    "alert_config",
    "alert_state",
    "alert_threshold",
    "alert_event" if hasattr(models, "AlertEvent") else None,
]
missing = [t for t in required_tables if t and t not in insp.get_table_names()]

if missing:
    console.print(f"[bold red]✗[/] Missing tables: {', '.join(missing)}")
    sys.exit(2)
console.print(f"[bold green]✓[/] All required tables present")

# ----------------------------------------------------------------------
# 3. Basic row counts
# ----------------------------------------------------------------------
with engine.connect() as conn:
    counts = {
        tbl: conn.execute(sqlalchemy.text(f"SELECT COUNT(*) FROM {tbl}")).scalar_one()
        for tbl in required_tables
        if tbl
    }

table = Table(title="Alert V2 Table Counts")
table.add_column("Table")
table.add_column("Rows", justify="right")
for t, c in counts.items():
    table.add_row(t, str(c))
console.print(table)

# ----------------------------------------------------------------------
# 4. Smoke‑test orchestrator loop in a transaction savepoint
# ----------------------------------------------------------------------
from contextlib import nullcontext

# Dummy metric resolver – always 999 so levels flip to HIGH
def _metric_resolver(cfg: AlertConfig) -> float:
    return 999.0

# No‑op notifier
def _noop_notifier(event):
    console.log(f" [dim]Event dispatched[/] → {event.level} {event.metric_value}")

from importlib import import_module

orch_mod = import_module(f"{alert_pkg.__name__}.orchestrator")
MetricFeedAdapter = orch_mod.MetricFeedAdapter
NotificationRouter = orch_mod.NotificationRouter
AlertOrchestrator = orch_mod.AlertOrchestrator

metrics = MetricFeedAdapter(metric_fn=_metric_resolver)
router = NotificationRouter(send_fn=_noop_notifier)
orch = AlertOrchestrator(repo, metrics, router)

# Wrap everything in a transaction so we can roll back demo rows
sess = repo.session
with sess.begin_nested():
    try:
        # If no alert configs exist, create throwaway entries directly within session
        if counts["alert_config"] == 0:
            cfg_row = models.AlertConfigTbl(
                id=f"demo-{uuid4()}",
                alert_type="TravelPercent",
                alert_class="Position",
                trigger_value=90,
                condition=models.Condition.ABOVE,
            )
            sess.add(cfg_row)

            state_row = models.AlertStateTbl(
                alert_id=cfg_row.id,
                last_level=models.AlertLevel.NORMAL
            )
            sess.add(state_row)

            th_row = models.ThresholdTbl(
                id=f"th-{uuid4()}",
                alert_type=cfg_row.alert_type,
                alert_class=cfg_row.alert_class,
                metric_key="travel_percent",
                condition=models.Condition.ABOVE,
                low=50,
                medium=70,
                high=90,
            )
            sess.add(th_row)

            sess.flush()  # commit temporarily within savepoint

            console.print("[yellow]⚠  No configs found – inserted demo alert & threshold[/]")

        orch.run_cycle()
        console.print("[bold green]✓[/] Orchestrator cycle executed without exception")
    except Exception as exc:
        console.print_exception(show_locals=False)
        console.print("[bold red]✗[/] Orchestrator cycle failed")
        sess.rollback()
        sys.exit(3)

    new_events = repo.last_events(limit=5)
    console.print(f"[bold cyan]ℹ[/] Last event: {new_events[0].level} at {new_events[0].created_at}"
                  if new_events else "[yellow]No events generated[/]")

# Transaction rolls back here – db unchanged
sess.rollback()

# ----------------------------------------------------------------------
# 5. Summary & next steps
# ----------------------------------------------------------------------
console.rule("[bold]Summary")
if missing:
    console.print("[bold red]DB schema incomplete – run Alembic migration[/]")
elif counts["alert_threshold"] == 0:
    console.print("[yellow]No thresholds found – seed alert_threshold rows next[/]")
elif counts["alert_config"] == 0:
    console.print("[yellow]No alert configs defined – create alerts via UI / seed script[/]")
else:
    console.print("[bold green]Alert V2 core looks healthy![/]  🎉")

console.print("\nRun this script after each deploy to verify schema + orchestrator health.")
