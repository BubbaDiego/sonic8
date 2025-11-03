from __future__ import annotations
"""
Sonic reporting sequencer (panel loader, compat, no write_line dependency)
- Accepts legacy positional style and new keyword args
- Renders: banner_panel, price_panel, positions_panel, positions_totals_panel,
           monitor_panel (summary), xcom_panel, wallets_panel, sync_panel
- Missing modules are skipped with a one-liner; never raises
"""

from typing import Any, Iterable, Mapping
import importlib
import inspect

__all__ = [
    "render_startup_banner",
    "render_cycle",
    "render_xcom_panel",
    "render_monitor_panel",
    "render_positions_totals_panel",
    "render_wallets_panel",
]


def _pkg_base() -> str:
    # e.g. backend.core.reporting_core.sonic_reporting
    return __name__.rsplit(".", 1)[0]


def _import_sibling(mod_name: str):
    """Import a sibling module. Return module or None; do not raise to caller."""
    try:
        return importlib.import_module(f".{mod_name}", package=_pkg_base())
    except Exception:
        return None


def _call_best_fn(mod, fn_names: Iterable[str], **kwargs) -> bool:
    """
    Try to call the first present function from fn_names on the module.
    Only pass parameters that the function actually accepts.
    """
    for fn_name in fn_names:
        fn = getattr(mod, fn_name, None)
        if callable(fn):
            try:
                sig = inspect.signature(fn)
                filtered = {k: v for k, v in kwargs.items() if k in sig.parameters}
                fn(**filtered)
                return True
            except Exception:
                continue
    return False


def _try_render(mod_name: str, *, debug_label: str | None = None, **kwargs) -> bool:
    """Import sibling and attempt its renderer; log a one-liner on skip; never raise."""
    m = _import_sibling(mod_name)
    if m is None:
        print(f"[SEQ] skip: {mod_name} (module not found)")
        return False

    # choose likely renderer names per module
    if mod_name == "banner_panel":
        names = ("render", "render_banner", "print_banner")
    elif mod_name == "monitor_panel":
        names = ("render", "render_monitors_summary")
    elif mod_name == "xcom_panel":
        names = ("render", "render_xcom_check")
    elif mod_name == "price_panel":
        names = ("render", "render_prices")
    elif mod_name == "positions_panel":
        names = ("render", "render_positions", "render_table")
    elif mod_name == "positions_totals_panel":
        names = ("render", "render_totals")
    elif mod_name == "wallets_panel":
        names = ("render", "render_wallets")
    elif mod_name == "sync_panel":
        names = ("render",)
    else:
        names = ("render",)

    ok = _call_best_fn(m, names, **kwargs)
    if not ok:
        lbl = debug_label or mod_name
        print(f"[SEQ] skip: {lbl} (no callable renderer)")
    return ok


# ---------- public API expected by sonic_monitor.py ----------

def render_startup_banner(*args, **kwargs) -> None:
    """
    Back-compat:
      legacy: render_startup_banner(dl, default_json_path)
      new   : render_startup_banner(dl=..., default_json_path=...)
    """
    dl = kwargs.get("dl")
    default_json_path = kwargs.get("default_json_path")
    if dl is None and len(args) >= 1: dl = args[0]
    if default_json_path is None and len(args) >= 2: default_json_path = args[1]

    _try_render("banner_panel", dl=dl, default_json_path=default_json_path, debug_label="banner_panel")


def render_cycle(*args, **kwargs) -> None:
    """
    Back-compat:
      legacy: render_cycle(dl, csum, default_json_path, ...)
      new   : render_cycle(dl=..., csum=..., default_json_path=..., ...)

    Optional toggles (default True unless noted):
      show_banner            (default False here; banner is typically startup-only)
      show_price_panel
      show_positions_panel
      show_positions_totals_panel
      show_monitor_panel
      show_xcom_panel
      show_wallets_panel
      show_sync_panel
    """
    # Known kwargs
    dl = kwargs.pop("dl", None)
    csum = kwargs.pop("csum", None) or kwargs.pop("summary", None)
    default_json_path = kwargs.pop("default_json_path", None)

    # Toggles
    show_banner                  = kwargs.pop("show_banner", False)
    show_price_panel             = kwargs.pop("show_price_panel", True)
    show_positions_panel         = kwargs.pop("show_positions_panel", True) or kwargs.pop("show_positions_table", kwargs.get("show_positions_table", True))
    show_positions_totals_panel  = kwargs.pop("show_positions_totals_panel", True) or kwargs.pop("show_positions_totals", kwargs.get("show_positions_totals", True))
    show_monitor_panel           = kwargs.pop("show_monitor_panel", True) or kwargs.pop("show_monitors_summary", kwargs.get("show_monitors_summary", True))
    show_xcom_panel              = kwargs.pop("show_xcom_panel", True) or kwargs.pop("show_xcom_check", kwargs.get("show_xcom_check", True))
    show_wallets_panel           = kwargs.pop("show_wallets_panel", True)
    show_sync_panel              = kwargs.pop("show_sync_panel", False)

    # Map legacy positional args
    if dl is None and len(args) >= 1: dl = args[0]
    if csum is None and len(args) >= 2: csum = args[1]
    if default_json_path is None and len(args) >= 3: default_json_path = args[2]

    # ---- sequence ----
    if show_banner:
        _try_render("banner_panel", dl=dl, default_json_path=default_json_path, debug_label="banner_panel")

    if show_price_panel:
        _try_render("price_panel", dl=dl, csum=csum, default_json_path=default_json_path, debug_label="price_panel")

    if show_positions_panel:
        _try_render("positions_panel", dl=dl, csum=csum, default_json_path=default_json_path, debug_label="positions_panel")

    _try_render(
        "raydium_panel",
        dl=dl,
        csum=csum,
        default_json_path=default_json_path,
        debug_label="raydium_panel"
    )
    if show_positions_totals_panel:
        _try_render("positions_totals_panel", dl=dl, csum=csum, default_json_path=default_json_path, debug_label="positions_totals_panel")

    if show_monitor_panel:
        _try_render("monitor_panel", dl=dl, csum=csum, default_json_path=default_json_path, debug_label="monitor_panel")

    if show_xcom_panel:
        _try_render("xcom_panel", dl=dl, csum=csum, default_json_path=default_json_path, debug_label="xcom_panel")

    if show_wallets_panel:
        _try_render("wallets_panel", dl=dl, csum=csum, default_json_path=default_json_path, debug_label="wallets_panel")

    if show_sync_panel:
        _try_render("sync_panel", dl=dl, csum=csum, default_json_path=default_json_path, debug_label="sync_panel")


# ---------- optional pass-throughs ----------

def render_xcom_panel(*, dl: Any, csum: Mapping[str, Any] | None = None,
                      default_json_path: str | None = None, **_: Any) -> None:
    _try_render("xcom_panel", dl=dl, csum=csum, default_json_path=default_json_path, debug_label="xcom_panel")

def render_monitor_panel(*, dl: Any, csum: Mapping[str, Any] | None = None,
                         default_json_path: str | None = None, **_: Any) -> None:
    _try_render("monitor_panel", dl=dl, csum=csum, default_json_path=default_json_path, debug_label="monitor_panel")

def render_positions_totals_panel(*, dl: Any, csum: Mapping[str, Any] | None = None,
                                  default_json_path: str | None = None, **_: Any) -> None:
    _try_render("positions_totals_panel", dl=dl, csum=csum, default_json_path=default_json_path, debug_label="positions_totals_panel")

def render_wallets_panel(*, dl: Any, csum: Mapping[str, Any] | None = None,
                         default_json_path: str | None = None, **_: Any) -> None:
    _try_render("wallets_panel", dl=dl, csum=csum, default_json_path=default_json_path, debug_label="wallets_panel")

