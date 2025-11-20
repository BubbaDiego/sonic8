from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple


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
    PanelInfo("preflight", "Pre-Flight Config", "🧪"),
    PanelInfo("monitors", "Monitors", "🔎"),
    PanelInfo("session", "Session / Goals", "🎯"),
    PanelInfo("market", "Market Alerts", "💹"),
    PanelInfo("xcom", "XCom", "✉️"),
    PanelInfo("wallets", "Wallets", "💼"),
]


# A small, safe palette of colors and table/border styles to choose from.
_COLOR_OPTIONS: List[Tuple[str, str]] = [
    ("default", "Default terminal color"),
    ("white", "White"),
    ("bright_white", "Bright white"),
    ("cyan", "Cyan"),
    ("bright_cyan", "Bright cyan"),
    ("magenta", "Magenta"),
    ("bright_magenta", "Bright magenta"),
    ("pink", "Pink"),
    ("hot_pink", "Hot pink"),
    ("yellow", "Yellow"),
    ("bright_yellow", "Bright yellow"),
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


# Simple ANSI color codes to show sample text in the color it represents.
_COLOR_ANSI = {
    "default": "",
    "white": "\033[37m",
    "bright_white": "\033[97m",
    "cyan": "\033[36m",
    "bright_cyan": "\033[96m",
    "magenta": "\033[35m",
    "bright_magenta": "\033[95m",
    "pink": "\033[95m",  # ANSI can't do true pink; map to bright magenta
    "hot_pink": "\033[95m",  # same here
    "yellow": "\033[33m",
    "bright_yellow": "\033[93m",
    "grey50": "\033[90m",
}


def _color_sample(value: str, text: str) -> str:
    """
    Wrap sample text in an ANSI color based on the config value.

    For non-color values (e.g. border styles), returns the text unchanged.
    """
    code = _COLOR_ANSI.get(value, "")
    if not code:
        return text
    return f"{code}{text}\033[0m"


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
    if not isinstance(cfg.get("panel_order"), list):
        cfg["panel_order"] = [p.slug for p in _PANELS]
    return cfg


def _ensure_defaults(cfg: Dict[str, Any]) -> Dict[str, Any]:
    defaults = cfg.setdefault("defaults", {})
    title = defaults.setdefault("title", {})
    body = defaults.setdefault("body", {})
    table = body.setdefault("table", {})

    # Provide some reasonable fallbacks if missing
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
    """
    Return _PANELS ordered according to cfg['panel_order'], with any missing
    slugs appended in their default order.
    """
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


# ─────────────────────────── panel toggling UI ──────────────────────────────


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
        # default: enabled unless explicitly False
        mark = "x" if enabled is not False else " "
        print(f"  {i}. [{mark}] {p.icon} {p.label} ({p.slug})")
    print()
    print("Actions:")
    print("  [#] Toggle panel enabled/disabled")
    print("  [G] Global style settings")
    print("  [R] Reorder panels")
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

    # Default effective state: enabled (when key missing)
    # Toggle logic:
    #   None / True  -> False
    #   False        -> True
    if enabled is False:
        new_enabled = True
    else:
        new_enabled = False

    pdata["enabled"] = new_enabled
    panels[p.slug] = pdata
    cfg["panels"] = panels

    state = "enabled" if new_enabled else "disabled"
    print(f"{p.icon} {p.label} is now {state}.")


def _reorder_panels(cfg: Dict[str, Any]) -> None:
    """Prompt the user for a new panel order (comma-separated positions)."""
    ordered = _get_ordered_panels(cfg)
    n = len(ordered)

    print("\nReorder panels")
    print("----------------")
    print("Current order:")
    for idx, p in enumerate(ordered, start=1):
        print(f"  {idx} → {p.slug}")

    print()
    print(
        f"Enter new order as {n} comma-separated numbers, e.g. "
        + ", ".join(str(i) for i in range(1, n + 1))
    )
    raw = input("New order → ").strip()
    if not raw:
        print("No changes made.")
        return

    parts = [x.strip() for x in raw.split(",") if x.strip()]
    if len(parts) != n:
        print("You must provide exactly one position for each panel.")
        input("Press ENTER to continue…")
        return

    try:
        positions = [int(p) for p in parts]
    except ValueError:
        print("All entries must be integers.")
        input("Press ENTER to continue…")
        return

    if sorted(positions) != list(range(1, n + 1)):
        print(f"Positions must be a permutation of 1..{n}.")
        input("Press ENTER to continue…")
        return

    new_order = [ordered[pos - 1].slug for pos in positions]
    cfg["panel_order"] = new_order
    print("Panel order updated.")
    input("Press ENTER to continue…")


# ───────────────────────── global style UI (defaults) ───────────────────────


def _pick_from_options(
    label: str, options: List[Tuple[str, str]], current: str
) -> str:
    """Utility to choose from a numbered list of (value, description)."""
    print(f"\n{label} (current: {current})")
    for i, (val, desc) in enumerate(options, start=1):
        mark = "*" if val == current else " "
        # Show the description in the color it represents (if applicable).
        sample_desc = _color_sample(val, desc)
        print(f"  {i}. [{mark}] {sample_desc} ({val})")
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
        print("\n🎨  Global Style Settings")
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
                "TITLE border style", _BORDER_STYLE_OPTIONS, title.get("border_style", "square")
            )
            title["border_style"] = new_val
        elif choice == "2":
            new_val = _pick_from_options(
                "TITLE border color", _COLOR_OPTIONS, title.get("border_color", "grey50")
            )
            title["border_color"] = new_val
        elif choice == "3":
            new_val = _pick_from_options(
                "TITLE text color", _COLOR_OPTIONS, title.get("text_color", "white")
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

        # persist after each change so Sonic Monitor picks it up via mtime
        _save_config(cfg)
        # re-resolve defaults for subsequent iterations
        cfg = _ensure_defaults(_load_config())
        defaults = cfg["defaults"]
        title = defaults["title"]
        body = defaults["body"]
        table = body["table"]


# ───────────────────────────── entrypoint ───────────────────────────────────


def run() -> None:
    """
    Entry point for the Panel Manager console.

    - Lets you toggle panel enabled/disabled flags.
    - Allows editing of GLOBAL title/body/table style settings via defaults
      in panel_config.json.
    """
    cfg = _load_config()
    cfg = _ensure_panel_blocks(cfg)
    cfg = _ensure_defaults(cfg)

    while True:
        _print_panels(cfg)
        choice = input("Select panel #, [G]lobal style, [R]eorder, or 0 to return → ").strip().lower()

        if choice in ("0", "q"):
            break

        if choice == "g":
            _global_style_menu(cfg)
            # reload after global changes
            cfg = _ensure_panel_blocks(_ensure_defaults(_load_config()))
            continue

        if choice == "r":
            _reorder_panels(cfg)
            _save_config(cfg)
            cfg = _ensure_panel_blocks(_ensure_defaults(_load_config()))
            continue

        if not choice:
            continue

        try:
            idx = int(choice)
        except ValueError:
            print("Please enter a number, 'G', or 'R'.")
            continue

        _toggle_panel(cfg, idx)
        _save_config(cfg)
        # config is mutated in place; loop will re-print with updated marks

    print("Returning to LaunchPad…")
