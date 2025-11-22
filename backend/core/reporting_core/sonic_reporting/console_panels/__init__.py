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
from . import raydium_panel


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
        label="Raydium LPs",
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
]

PANEL_REGISTRY: Dict[str, PanelSpec] = {spec.key: spec for spec in PANEL_SPECS}
PANELS_BY_SLUG: Dict[str, PanelSpec] = {spec.slug: spec for spec in PANEL_SPECS}
PANEL_KEYS: List[str] = list(PANEL_REGISTRY.keys())


__all__ = [
    "console_width",
    "hr",
    "title_lines",
    "get_panel_title_config",
    "blast_panel",
    "raydium_panel",
    "PanelSpec",
    "PANEL_SPECS",
    "PANEL_REGISTRY",
    "PANELS_BY_SLUG",
    "PANEL_KEYS",
]
