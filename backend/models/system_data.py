"""System variables data model."""
from dataclasses import dataclass
from typing import Optional

@dataclass
class SystemVariables:
    """Represents the row in the ``system_vars`` table."""

    last_update_time_positions: Optional[str] = None
    last_update_positions_source: Optional[str] = None
    last_update_time_prices: Optional[str] = None
    last_update_prices_source: Optional[str] = None
    last_update_time_jupiter: Optional[str] = None
    last_update_jupiter_source: Optional[str] = None
    theme_mode: str = "light"
    theme_active_profile: Optional[str] = None
    strategy_start_value: Optional[float] = None
    strategy_description: Optional[str] = None


__all__ = ["SystemVariables"]
