from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from backend.core.core_constants import SONIC_MONITOR_CONFIG_PATH


# Basic panel metadata for display; slugs must match panel_config.json.
@dataclass
class PanelInfo:
    slug: str
    label: str
    icon: str


# Keep this list aligned with the slugs used in panel_config.json.
_PANELS: List[PanelInfo] = [
    PanelInfo("activity", "Cycle Activity", "📘"),
    PanelInfo("prices", "Prices", "💵"),
    PanelInfo("positions", "Positions", "📊"),
    PanelInfo("risk", "Risk Snapshot", "⚖️"),
    PanelInfo("transition", "Transitions", "🔄"),
    PanelInfo("preflight", "Pre-Flight Config", "🧪"),
    PanelInfo("monitors", "Monitors", "🔎"),
    PanelInfo("blast", "Blast Radius", "💥"),
    PanelInfo("market", "Market Alerts", "💹"),
    PanelInfo("session", "Session / Goals", "🎯"),
    PanelInfo("xcom", "XCom", "✉️"),
    PanelInfo("wallets", "Wallets", "💼"),
]


# Small, safe palette of colors and table/border styles to choose from.
_COLOR_OPTIONS: List[Tuple[str, str]] = [
    ("default", "Default terminal color"),
    ("white", "White"),
    ("bright_white", "Bright white"),
    ("cyan", "Cyan"),
    ("magenta", "Magenta"),
    ("yellow", "Yellow"),
    ("grey50", "Grey 50"),
]

_BORDER_STYLE_OPTIONS: List[Tuple[str, str]] = [
    ("square", "Square"),
    ("rounded", "Rounded"),
    ("none", "None"),
]

_TABLE_STYLE_OPTIONS: List[Tuple[str, str]] = [
    ("thin", "Thin (simple head)"),
    ("thick", "Thick (heavy head)"),
    ("invisible", "Invisible (no borders)"),
]


# For pretty printing the current choice.
_COLOR_DISPLAY_NAME = {
    "default": "default",
    "white": "white",
    "bright_white": "bright_white",
    "cyan": "cyan",
    "magenta": "magenta",
    "yellow": "yellow",
    "grey50": "grey50",
}


# Simple colorization for menu (no-op if not supported by terminal).
_COLOR_CODES = {
    "default": "",
    "white": "\033[37m",
    "bright_white": "\033[97m",
    "cyan": "\033[36m",
    "magenta": "\033[35m",
    "yellow": "\033[33m",
    "grey50": "\033[38;5;244m",
}


def _color_label(kind: str, value: str) -> str:
    code = _COLOR_CODES.get(value, "")
    reset = "\033[0m" if code else ""
    if kind == "border":
        base = f"{value}"
    else:
        base = f"{value}"
    return f"{code}{base}{reset}"


# ───────────────────────── monitor console config helpers ─────────────────────────


def _load_monitor_console_cfg() -> dict:
    """
    Load sonic_monitor_config.json and return its top-level dict.

    This is a light-weight loader for console settings. We only care about:
      monitor.console.clear_each_cycle
    """
    cfg_path = Path(SONIC_MONITOR_CONFIG_PATH)
    try:
        raw = cfg_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}

    try:
        data = json.loads(raw) or {}
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _save_monitor_console_cfg(cfg: dict) -> None:
    """
    Persist sonic_monitor_config.json after in-place modification.

    Keeps formatting simple but deterministic (indent=2, sorted keys).
    """
    cfg_path = Path(SONIC_MONITOR_CONFIG_PATH)
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(cfg, indent=2, sort_keys=True)
    cfg_path.write_text(text + "\n", encoding="utf-8")


def get_console_clear_each_cycle() -> bool:
    """
    Return True if monitor console is configured to clear each cycle
    (dashboard mode); False means continuous scroll mode.
    """
    cfg = _load_monitor_console_cfg()
    monitor_cfg = cfg.get("monitor") or {}
    if not isinstance(monitor_cfg, dict):
        monitor_cfg = {}
    console_cfg = monitor_cfg.get("console") or {}
    if not isinstance(console_cfg, dict):
        console_cfg = {}
    return bool(console_cfg.get("clear_each_cycle", False))


def toggle_console_clear_each_cycle() -> bool:
    """
    Toggle monitor.console.clear_each_cycle in sonic_monitor_config.json.

    Returns the new value (True = clear each cycle, False = continuous scroll).
    """
    cfg = _load_monitor_console_cfg()
    monitor_cfg = cfg.get("monitor")
    if not isinstance(monitor_cfg, dict):
        monitor_cfg = {}
        cfg["monitor"] = monitor_cfg

    console_cfg = monitor_cfg.get("console")
    if not isinstance(console_cfg, dict):
        console_cfg = {}
        monitor_cfg["console"] = console_cfg

    current = bool(console_cfg.get("clear_each_cycle", False))
    new_val = not current
    console_cfg["clear_each_cycle"] = new_val

    _save_monitor_console_cfg(cfg)
    return new_val


# ─────────────────────────── config plumbing ────────────────────────────────


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
    # Ensure panel_order exists and contains all slugs
    if not isinstance(cfg.get("panel_order"), list):
        cfg["panel_order"] = [p.slug for p in _PANELS]
    else:
        order = [str(s) for s in cfg["panel_order"]]
        for p in _PANELS:
            if p.slug not in order:
                order.append(p.slug)
        cfg["panel_order"] = order
    return cfg


def _ensure_defaults(cfg: Dict[str, Any]) -> Dict[str, Any]:
    defaults = cfg.setdefault("defaults", {})
    title = defaults.setdefault("title", {})
    body = defaults.setdefault("body", {})
    table = body.setdefault("table", {})

    title.setdefault("border_style", "square")
    title.setdefault("border_color", "grey50")
    title.setdefault("text_color", "white")
    title.setdefault("align", "center")

    body.setdefault("column_header_text_color", "cyan")
    body.setdefault("body_text_color", "default")
    body.setdefault("totals_row_color", "grey50")

    table.setdefault("style", "thin")
    table.setdefault("table_justify", "left")
    table.setdefault("header_justify", "left")

    return cfg


def _get_ordered_panels(cfg: Dict[str, Any]) -> List[PanelInfo]:
    """Return _PANELS ordered according to cfg['panel_order']."""
    order = cfg.get("panel_order")
    slug_to_panel = {p.slug: p for p in _PANELS}
    ordered: List[PanelInfo] = []

    if isinstance(order, list):
        for slug in order:
            p = slug_to_panel.get(str(slug))
            if p is not None and p not in ordered:
                ordered.append(p)

    for p in _PANELS:
        if p not in ordered:
            ordered.append(p)

    return ordered


# ─────────────────────────── panel list & toggling ──────────────────────────


def _print_panels(cfg: Dict[str, Any]) -> None:
    panels_cfg = cfg.get("panels") or {}
    ordered = _get_ordered_panels(cfg)

    print()
    print("🎛  Panel Manager")
    print("----------------")
    print()
    for i, p in enumerate(ordered, start=1):
        pdata = panels_cfg.get(p.slug) or {}
        enabled = pdata.get("enabled")
        mark = "x" if enabled is not False else " "
        print(f"  {i}. [{mark}] {p.icon} {p.label} ({p.slug})")
    print()
    print("Actions:")
    clear_mode = get_console_clear_each_cycle()
    if clear_mode:
        mode_label = "Clear each cycle (dashboard mode)"
    else:
        mode_label = "Continuous scroll (log mode)"

    print("  [#] Select panel to toggle / move")
    print("  [G] Global style settings")
    print(f"  [C] Console mode: {mode_label}")
    print("  [0] ⏪ Back")
    print()


def _toggle_panel(cfg: Dict[str, Any], idx: int) -> None:
    panels = cfg.get("panels") or {}
    ordered = _get_ordered_panels(cfg)
    if idx < 1 or idx > len(ordered):
        print("Invalid panel number.")
        return

    p = ordered[idx - 1]
    pdata = panels.get(p.slug) or {}
    enabled = pdata.get("enabled")

    # Default effective state: enabled when key missing
    if enabled is False:
        new_enabled = True
    else:
        new_enabled = False

    pdata["enabled"] = new_enabled
    panels[p.slug] = pdata
    cfg["panels"] = panels

    state = "enabled" if new_enabled else "disabled"
    print(f"{p.icon} {p.label} is now {state}.")


def _move_panel(cfg: Dict[str, Any], idx: int, delta: int) -> int:
    """Move panel at position idx up/down by delta; return new index."""
    ordered = _get_ordered_panels(cfg)
    n = len(ordered)
    i = idx - 1
    j = i + delta
    if j < 0 or j >= n:
        print("Already at the edge; cannot move further.")
        return idx

    # swap entries
    ordered[i], ordered[j] = ordered[j], ordered[i]
    cfg["panel_order"] = [p.slug for p in ordered]
    return j + 1  # new index


def _panel_detail_menu(cfg: Dict[str, Any], idx: int) -> None:
    """Per-panel mini menu: toggle / move up / move down."""
    while True:
        ordered = _get_ordered_panels(cfg)
        if idx < 1 or idx > len(ordered):
            print("Invalid panel number.")
            return
        p = ordered[idx - 1]
        panels = cfg.get("panels") or {}
        pdata = panels.get(p.slug) or {}
        enabled = pdata.get("enabled") is not False

        print()
        print(f"Selected: {idx}. [{'x' if enabled else ' '}] {p.icon} {p.label} ({p.slug})")
        print("  1) Toggle enabled/disabled")
        print("  2) Move up")
        print("  3) Move down")
        print("  0) ⏪ Back to panel list")
        choice = input("→ ").strip()

        if choice in ("0", "q"):
            break
        elif choice == "1":
            _toggle_panel(cfg, idx)
        elif choice == "2":
            idx = _move_panel(cfg, idx, -1)
        elif choice == "3":
            idx = _move_panel(cfg, idx, +1)
        else:
            print("Unknown choice.")


# ───────────────────────── global style UI (defaults) ───────────────────────


def _pick_from_options(
    label: str, options: List[Tuple[str, str]], current: str
) -> str:
    print(f"\n{label} (current: {current})")
    for i, (val, desc) in enumerate(options, start=1):
        mark = "*" if val == current else " "
        # colorize value label a bit
        print(f"  {i}. [{mark}] {_color_label(label.split()[0].upper(), val)} ({val})")
    print("  0. ⏪ Back (keep current)")
    raw = input("Select # → ").strip()
    if not raw or raw == "0":
        return current
    try:
        idx = int(raw)
    except ValueError:
        return current
    if 1 <= idx <= len(options):
        return options[idx - 1][0]
    return current


def _global_style_menu(cfg: Dict[str, Any]) -> None:
    cfg = _ensure_defaults(cfg)
    defaults = cfg["defaults"]
    title = defaults["title"]
    body = defaults["body"]
    table = body["table"]

    while True:
        print("\n🎨 Global Style Settings")
        print("------------------------")
        print()
        print("TITLE")
        print(f"  1) Border style : {title.get('border_style')}")
        print(f"  2) Border color : {title.get('border_color')}")
        print(f"  3) Text color   : {title.get('text_color')}")
        print()
        print("BODY")
        print(f"  4) Header color : {body.get('column_header_text_color')}")
        print(f"  5) Body color   : {body.get('body_text_color')}")
        print(f"  6) Totals color : {body.get('totals_row_color')}")
        print()
        print("TABLE")
        print(f"  7) Style        : {table.get('style')}")
        print()
        print("  0) ⏪ Back")

        choice = input("Select setting to change → ").strip().lower()

        if choice in ("0", "q"):
            break
        elif choice == "1":
            new_val = _pick_from_options(
                "TITLE border style",
                _BORDER_STYLE_OPTIONS,
                title.get("border_style", "square"),
            )
            title["border_style"] = new_val
        elif choice == "2":
            new_val = _pick_from_options(
                "TITLE border color",
                _COLOR_OPTIONS,
                title.get("border_color", "grey50"),
            )
            title["border_color"] = new_val
        elif choice == "3":
            new_val = _pick_from_options(
                "TITLE text color",
                _COLOR_OPTIONS,
                title.get("text_color", "white"),
            )
            title["text_color"] = new_val
        elif choice == "4":
            new_val = _pick_from_options(
                "BODY header color",
                _COLOR_OPTIONS,
                body.get("column_header_text_color", "cyan"),
            )
            body["column_header_text_color"] = new_val
        elif choice == "5":
            new_val = _pick_from_options(
                "BODY body text color",
                _COLOR_OPTIONS,
                body.get("body_text_color", "default"),
            )
            body["body_text_color"] = new_val
        elif choice == "6":
            new_val = _pick_from_options(
                "BODY totals row color",
                _COLOR_OPTIONS,
                body.get("totals_row_color", "grey50"),
            )
            body["totals_row_color"] = new_val
        elif choice == "7":
            new_val = _pick_from_options(
                "TABLE style",
                _TABLE_STYLE_OPTIONS,
                table.get("style", "thin"),
            )
            table["style"] = new_val
        else:
            print("Unknown choice.")
            continue

        _save_config(cfg)
        cfg = _ensure_defaults(_load_config())
        defaults = cfg["defaults"]
        title = defaults["title"]
        body = defaults["body"]
        table = body["table"]


# ───────────────────────────── entrypoint ───────────────────────────────────


def run() -> None:
    """
    Entry point for the Panel Manager console.

    - Shows current panels in configured order.
    - Lets you select a panel, then toggle enabled / move up / move down.
    - Provides a global style editor for TITLE/BODY/TABLE defaults.
    """
    cfg = _ensure_panel_blocks(_ensure_defaults(_load_config()))

    while True:
        _print_panels(cfg)
        choice = input(
            "Select panel #, [G]lobal style, [C]onsole mode, or 0 to return → "
        ).strip().lower()

        if choice in ("0", "q"):
            break

        if choice == "g":
            _global_style_menu(cfg)
            cfg = _ensure_panel_blocks(_ensure_defaults(_load_config()))
            continue

        if choice == "c":
            new_val = toggle_console_clear_each_cycle()
            if new_val:
                print(" Console mode set to: Clear each cycle (dashboard mode).")
            else:
                print(" Console mode set to: Continuous scroll (log mode).")
            input(" Press ENTER to continue...")

            cfg = _ensure_panel_blocks(_ensure_defaults(_load_config()))

            continue

        if not choice:
            continue

        try:
            idx = int(choice)
        except ValueError:
            print("Please enter a number, 'G', or 'C'.")
            continue

        _panel_detail_menu(cfg, idx)
        _save_config(cfg)
        cfg = _ensure_panel_blocks(_ensure_defaults(_load_config()))

    print("Returning to LaunchPad…")
