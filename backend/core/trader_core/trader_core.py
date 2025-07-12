"""Service layer for managing Trader creation and lifecycle."""

from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import importlib
from typing import List, Optional
from backend.data.learning_database.learning_event_logger import log_learning_event
import json

from backend.models.trader import Trader
from backend.core.trader_core.mood_engine import evaluate_mood
from backend.core.trader_core.trader_store import TraderStore
from backend.utils.time_utils import iso_utc_now

StrategyManager = importlib.import_module("oracle_core.strategy_manager").StrategyManager
PersonaManager = importlib.import_module("oracle_core.persona_manager").PersonaManager
OracleDataService = importlib.import_module("oracle_core.oracle_data_service").OracleDataService
CalcServices = importlib.import_module("calc_core.calc_services").CalcServices


class TraderCore:
    """Create, enrich, and persist Trader objects."""

    def __init__(
        self,
        data_locker,
        persona_manager: Optional[PersonaManager] = None,
        strategy_manager: Optional[StrategyManager] = None,
    ) -> None:
        self.data_locker = data_locker
        self.persona_manager = persona_manager or PersonaManager()
        self.strategy_manager = strategy_manager or StrategyManager()
        self.data_service = OracleDataService(data_locker)
        self.store = TraderStore()

    def create_trader(self, trader_name: str) -> Trader:
        """Construct a Trader from persona and current data."""
        persona = self.persona_manager.get(trader_name)
        wallet_name = persona.name + "Vault"
        wallet_data = None
        if self.data_locker and hasattr(self.data_locker, "get_wallet_by_name"):
            wallet_data = self.data_locker.get_wallet_by_name(wallet_name)
        positions = []
        if self.data_locker and getattr(self.data_locker, "positions", None):
            pm = self.data_locker.positions
            if hasattr(pm, "get_active_positions_by_wallet"):
                positions = pm.get_active_positions_by_wallet(wallet_name) or []
            else:
                positions = pm.get_all_positions() or []
        portfolio = self.data_service.fetch_portfolio() or {}
        calc = CalcServices()
        avg_heat = calc.calculate_weighted_heat_index(positions)
        mood = evaluate_mood(avg_heat, getattr(persona, "moods", {}))
        score = max(0, int(100 - avg_heat))
        wallet_balance = (
            wallet_data.get("balance", 0.0) if isinstance(wallet_data, dict) else 0.0
        )
        wallet_balance += sum(float(p.get("value") or 0.0) for p in positions)
        total_profit = sum(calc.calculate_profit(p) for p in positions)
        born_on = iso_utc_now()
        initial_collateral = (
            wallet_data.get("balance", 0.0) if isinstance(wallet_data, dict) else 0.0
        )
        trader = Trader(
            name=persona.name,
            avatar=getattr(persona, "avatar", ""),
            color=getattr(persona, "color", ""),
            persona=getattr(persona, "profile", persona.name),
            origin_story=getattr(persona, "origin_story", ""),
            risk_profile=getattr(persona, "risk_profile", ""),
            mood=mood,
            moods=getattr(persona, "moods", {}),
            strategies=persona.strategy_weights,
            strategy_notes="",
            wallet=wallet_data.get("name") if isinstance(wallet_data, dict) else wallet_name,
            wallet_balance=round(wallet_balance, 2),
            profit=round(total_profit, 2),
            portfolio=portfolio,
            positions=positions,
            hedges=[],
            performance_score=score,
            heat_index=avg_heat,
            born_on=born_on,
            initial_collateral=initial_collateral,
        )
        return trader

    def save_trader(self, trader: Trader) -> bool:
        success = self.store.save(trader)
        if success:
            self._log_snapshot(trader)
        return success

    def get_trader(self, name: str) -> Optional[Trader]:
        """Retrieve an enriched Trader by name."""
        trader = self.store.get(name)
        if trader is None:
            trader = self.create_trader(name)
            self.store.save(trader)
        return trader

    def list_traders(self) -> List[Trader]:
        """Return Trader objects for all known personas."""
        names = self.persona_manager.list_personas()
        return [self.get_trader(n) for n in names]

    def delete_trader(self, name: str) -> bool:
        """Remove Trader metadata from the store."""
        return self.store.delete(name)

    def refresh_trader(self, name: str) -> Optional[Trader]:
        """Recompute wallet metrics for an existing Trader and persist them."""
        trader = self.store.get(name)
        if trader is None:
            return None

        wallet_name = trader.wallet
        positions = []
        if self.data_locker and getattr(self.data_locker, "positions", None):
            pm = self.data_locker.positions
            if hasattr(pm, "get_active_positions_by_wallet"):
                positions = pm.get_active_positions_by_wallet(wallet_name) or []
            else:
                positions = pm.get_all_positions() or []

        calc = CalcServices()
        avg_heat = calc.calculate_weighted_heat_index(positions)
        wallet_data = None
        if self.data_locker and hasattr(self.data_locker, "get_wallet_by_name"):
            wallet_data = self.data_locker.get_wallet_by_name(wallet_name)
        wallet_balance = (
            wallet_data.get("balance", 0.0) if isinstance(wallet_data, dict) else 0.0
        )
        wallet_balance += sum(float(p.get("value") or 0.0) for p in positions)
        total_profit = sum(calc.calculate_profit(p) for p in positions)
        trader.positions = positions
        trader.heat_index = avg_heat
        trader.performance_score = max(0, int(100 - avg_heat))
        trader.wallet_balance = round(wallet_balance, 2)
        trader.profit = round(total_profit, 2)

        if hasattr(self.data_locker, "traders"):
            self.data_locker.traders.update_trader(
                trader.name,
                {
                    "heat_index": trader.heat_index,
                    "performance_score": trader.performance_score,
                    "wallet_balance": trader.wallet_balance,
                    "profit": trader.profit,
                },
            )

        self.store.save(trader)
        self._log_snapshot(trader)
        return trader

    def _log_snapshot(self, t: Trader):
        log_learning_event("trader_snapshots", {
            "trader_name": t.name,
            "wallet_balance": t.wallet_balance,
            "portfolio_value": sum(p.get("value", 0) for p in t.positions),
            "heat_index": t.heat_index,
            "mood": t.mood,
            "strategy_json": json.dumps(t.strategies),
        })