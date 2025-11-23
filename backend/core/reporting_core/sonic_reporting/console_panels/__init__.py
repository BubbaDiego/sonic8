"""Console panel package utilities."""
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .theming import (
    console_width,
    hr,
    title_lines,
    get_panel_title_config,
)
from . import blast_panel
from . import market_panel
from . import monitor_panel
from . import positions_panel
from . import preflight_config_panel
from . import price_panel
from . import raydium_panel
from . import risk_panel
from . import session_panel
from . import sessions_panel
from .sessions_panel import build_sessions_panel
from . import transition_panel
from . import wallets_panel
from . import xcom_panel


@dataclass(frozen=True)
class PanelSpec:
    key: str
    slug: str
    label: str
    connector: Callable[..., Any]
    module: Any
    description: str = ""
    group: str = "sonic"
    module_path: Optional[str] = None


PANEL_SPECS: List[PanelSpec] = [
    PanelSpec(
        key="blast",
        slug="blast",
        label="Blast Radius",
        connector=getattr(
            blast_panel,
            "connector",
            getattr(blast_panel, "render", None),
        ),
        module=blast_panel,
        description="Blast Radius monitors (encroachment %, blast %, travel %, state).",
        group="defi",
        module_path="backend.core.reporting_core.sonic_reporting.console_panels.blast_panel",
    ),
    PanelSpec(
        key="raydium",
        slug="raydium",
        label="🌊 Raydium LPs",
        connector=getattr(
            raydium_panel,
            "connector",
            getattr(raydium_panel, "render", None),
        ),
        module=raydium_panel,
        description="Raydium LP positions (qty, USD, APR, last checked).",
        group="defi",
        module_path="backend.core.reporting_core.sonic_reporting.console_panels.raydium_panel",
    ),
    PanelSpec(
        key="sessions",
        slug="sessions",
        label="Sessions",
        connector=getattr(
            sessions_panel,
            "connector",
            getattr(sessions_panel, "build_sessions_panel", None),
        ),
        module=sessions_panel,
        description="Sessions overview matrix (PnL, returns, drawdown).",
        group="sonic",
        module_path="backend.core.reporting_core.sonic_reporting.console_panels.sessions_panel",
    ),
]

PANELS: Dict[str, Any] = {
    "prices": price_panel,
    "positions": positions_panel,
    "risk": risk_panel,
    "transition": transition_panel,
    "preflight": preflight_config_panel,
    "monitors": monitor_panel,
    "blast": blast_panel,
    "market": market_panel,
    "xcom": xcom_panel,
    "session": session_panel,
    "sessions": build_sessions_panel,
    "wallets": wallets_panel,
}

PANEL_REGISTRY: Dict[str, PanelSpec] = {spec.key: spec for spec in PANEL_SPECS}
PANELS_BY_SLUG: Dict[str, PanelSpec] = {spec.slug: spec for spec in PANEL_SPECS}
PANEL_KEYS: List[str] = list(PANEL_REGISTRY.keys())


__all__ = [
    "console_width",
    "hr",
    "title_lines",
    "get_panel_title_config",
    "blast_panel",
    "market_panel",
    "monitor_panel",
    "positions_panel",
    "preflight_config_panel",
    "price_panel",
    "raydium_panel",
    "risk_panel",
    "session_panel",
    "sessions_panel",
    "build_sessions_panel",
    "transition_panel",
    "wallets_panel",
    "xcom_panel",
    "PanelSpec",
    "PANEL_SPECS",
    "PANELS",
    "PANEL_REGISTRY",
    "PANELS_BY_SLUG",
    "PANEL_KEYS",
]
