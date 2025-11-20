from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


# Basic panel metadata for nice display; keys must match panel_config.json slugs.
@dataclass
class PanelInfo:
    slug: str
    label: str
    icon: str


# Keep in sync with panel_config.json "panels" keys.
_PANELS: List[PanelInfo] = [
    PanelInfo("activity", "Cycle Activity", "📘"),
    PanelInfo("prices", "Prices", "💵"),
    PanelInfo("positions", "Positions", "📊"),
    PanelInfo("risk", "Risk Snapshot", "⚖️"),
    PanelInfo("preflight", "Pre-Flight Config", "🧪"),
    PanelInfo("monitors", "Monitors", "🔎"),
    PanelInfo("session", "Session / Goals", "🎯"),
    PanelInfo("market", "Market Alerts", "💹"),
    PanelInfo("xcom", "XCom", "✉️"),
    PanelInfo("wallets", "Wallets", "💼"),
]


def _config_path() -> Path:
    default_path = Path(
        "backend/core/reporting_core/sonic_reporting/console_panels/panel_config.json"
    )
    env_path = os.getenv("PANEL_CONFIG_PATH")
    return Path(env_path) if env_path else default_path


def _load_config() -> Dict[str, Any]:
    path = _config_path()
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text) if text.strip() else {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_config(cfg: Dict[str, Any]) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(cfg, indent=2, sort_keys=True)
    path.write_text(text, encoding="utf-8")


def _ensure_panel_blocks(cfg: Dict[str, Any]) -> Dict[str, Any]:
    if "panels" not in cfg or not isinstance(cfg["panels"], dict):
        cfg["panels"] = {}
    panels = cfg["panels"]
    for p in _PANELS:
        panels.setdefault(p.slug, {})
    return cfg


def _print_panels(cfg: Dict[str, Any]) -> None:
    panels = cfg.get("panels") or {}
    print()
    print("🎛 Panel Manager")
    print("----------------")
    print()
    for i, p in enumerate(_PANELS, start=1):
        pdata = panels.get(p.slug) or {}
        enabled = pdata.get("enabled")
        # default: enabled unless explicitly False
        mark = "x" if enabled is not False else " "
        print(f"  {i}. [{mark}] {p.icon} {p.label} ({p.slug})")
    print()
    print("  0. ⏪ Back")


def _toggle_panel(cfg: Dict[str, Any], idx: int) -> None:
    if idx < 1 or idx > len(_PANELS):
        print("Invalid selection.")
        return
    panels = cfg.get("panels") or {}
    p = _PANELS[idx - 1]
    pdata = panels.get(p.slug) or {}
    enabled = pdata.get("enabled")
    # default: True, toggle to False; otherwise flip bool.
    new_enabled = not bool(enabled is False)
    pdata["enabled"] = new_enabled
    panels[p.slug] = pdata
    cfg["panels"] = panels
    state = "enabled" if new_enabled else "disabled"
    print(f"{p.icon} {p.label} is now {state}.")


def run() -> None:
    """
    Entry point for the Panel Manager console.

    Edits panel_config.json in-place (or the file pointed to by PANEL_CONFIG_PATH).
    Sonic Monitor will pick up changes on the next refresh cycle thanks to the
    mtime-aware theming config.
    """
    cfg = _load_config()
    cfg = _ensure_panel_blocks(cfg)

    while True:
        _print_panels(cfg)
        choice = input("Select panel # to toggle, or 0 to return → ").strip().lower()
        if choice in ("0", "q"):
            break
        if not choice:
            continue
        try:
            idx = int(choice)
        except ValueError:
            print("Please enter a number from the list.")
            continue

        _toggle_panel(cfg, idx)
        _save_config(cfg)
        # loop will reload view with updated config

    print("Returning to LaunchPad…")
