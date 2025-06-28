#!/usr/bin/env python3
"""Trigger a live risk alert using RiskMonitor.

This script inserts a dummy high-heat position and then runs
``RiskMonitor`` so that a HIGH level XCom notification is dispatched.
It removes the position afterwards. Use this to verify risk alert
delivery (voice call/SMS) through XCom.
"""
from __future__ import annotations

from uuid import uuid4
from datetime import datetime

from core.constants import MOTHER_DB_PATH
from data.data_locker import DataLocker
from monitor.risk_monitor import RiskMonitor


def verify_risk_alert() -> None:
    """Insert a risky position and run ``RiskMonitor``."""
    dl = DataLocker(MOTHER_DB_PATH)

    position = {
        "id": str(uuid4()),
        "asset_type": "TEST",
        "entry_price": 100.0,
        "current_price": 100.0,
        "liquidation_price": 50.0,
        "collateral": 100.0,
        "size": 1.0,
        "leverage": 1.0,
        "value": 100.0,
        "pnl_after_fees_usd": 0.0,
        "wallet_name": "verify_risk_alert",
        "position_type": "long",
        "last_updated": datetime.now().isoformat(),
        "is_active": True,
        "heat_index": 95.0,
    }

    dl.positions.create_position(position)

    try:
        monitor = RiskMonitor()
        monitor.run_cycle()
    finally:
        dl.positions.delete_position(position["id"])


if __name__ == "__main__":
    verify_risk_alert()
