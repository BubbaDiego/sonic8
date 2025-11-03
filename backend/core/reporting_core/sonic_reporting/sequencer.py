from __future__ import annotations
"""
Sequencer (compat & complete)
- Accepts legacy positional and new keyword styles.
- Renders: monitors_summary, xcom_check_panel, prices panel, positions table,
  positions totals, wallets panel (all optional; skip cleanly if missing).
- Ignores unknown kwargs; never crashes if a sub-renderer is absent.
"""

from typing import Any, Iterable, Mapping
import importlib
import inspect

__all__ = [
    "render_startup_banner",
    "render_cycle",
    "render_xcom_check_panel",
    "render_monitors_summary",
    "render_positions_totals",
    "render_wallets_panel",
]


# ---------- helpers ----------

def _pkg_base() -> str:
    # e.g. backend.core.reporting_core.sonic_reporting
    return __name__.rsplit(".", 1)[0]


def _import_sibling(mod_name: str):
    try:
        return importlib.import_module(f".{mod_name}", package=_pkg_base())
    except Exception:
        return None


def _call_best_fn(mod, fn_names: Iterable[str], **kwargs) -> bool:
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
    m = _import_sibling(mod_name)
    if m is None:
        print(f"[SEQ] skip: {mod_name} (module not found)")
        return False

    # pick likely renderer names per module
    if mod_name == "banner_config":
        names = ("render_banner", "render", "print_banner")
    elif mod_name == "monitors_summary":
        names = ("render", "render_monitors_summary")
    elif mod_name == "xcom_check_panel":
        names = ("render", "render_xcom_check")
    elif mod_name == "prices_panel":
        names = ("render", "render_prices", "render_price_panel")
    elif mod_name == "price_panel":
        names = ("render", "render_prices", "render_price_panel")
    elif mod_name == "positions_panel":
        names = ("render", "render_positions", "render_table")
    elif mod_name == "positions_table":
        names = ("render", "render_positions", "render_table")
    elif mod_name == "positions_totals":
        names = ("render", "render_totals")
    elif mod_name == "wallets_panel":
        names = ("render", "render_wallets")
    else:
        names = ("render",)

    ok = _call_best_fn(m, names, **kwargs)
    if not ok:
        lbl = debug_label or mod_name
        print(f"[SEQ] skip: {lbl} (no callable renderer)")
    return ok


# ---------- public API ----------

def render_startup_banner(*args, **kwargs) -> None:
    """
    Back-compat:
      legacy: render_startup_banner(dl, default_json_path)
      new   : render_startup_banner(dl=..., default_json_path=...)
    """
    dl = kwargs.get("dl")
    default_json_path = kwargs.get("default_json_path")

    if dl is None and len(args) >= 1:
        dl = args[0]
    if default_json_path is None and len(args) >= 2:
        default_json_path = args[1]

    _try_render(
        "banner_config",
        dl=dl,
        default_json_path=default_json_path,
        debug_label="startup_banner",
    )


def render_cycle(*args, **kwargs) -> None:
    """
    Back-compat:
      legacy: render_cycle(dl, csum, default_json_path, ...)
      new   : render_cycle(dl=..., csum=..., default_json_path=..., ...)

    Optional toggles (all default True):
      show_monitors_summary, show_xcom_check,
      show_prices_panel, show_positions_table, show_positions_totals,
      show_wallets_panel
    """
    # known kwargs
    dl = kwargs.pop("dl", None)
    csum = kwargs.pop("csum", None)
    default_json_path = kwargs.pop("default_json_path", None)

    # toggles
    show_monitors_summary = kwargs.pop("show_monitors_summary", True)
    show_xcom_check      = kwargs.pop("show_xcom_check", True)
    show_prices_panel    = kwargs.pop("show_prices_panel", True)
    show_positions_table = kwargs.pop("show_positions_table", True)
    show_positions_totals= kwargs.pop("show_positions_totals", True)
    show_wallets_panel   = kwargs.pop("show_wallets_panel", True)

    # positional mapping (legacy)
    if dl is None and len(args) >= 1:
        dl = args[0]
    if csum is None and len(args) >= 2:
        csum = args[1]
    if default_json_path is None and len(args) >= 3:
        default_json_path = args[2]

    # ---- sequence ----
    if show_monitors_summary:
        _try_render("monitors_summary", dl=dl, csum=csum, default_json_path=default_json_path,
                    debug_label="monitors_summary")

    if show_xcom_check:
        _try_render("xcom_check_panel", dl=dl, csum=csum, default_json_path=default_json_path,
                    debug_label="xcom_check_panel")

    # Prices panel (either module name)
    if show_prices_panel:
        if not _try_render("prices_panel", dl=dl, csum=csum, default_json_path=default_json_path,
                           debug_label="prices_panel"):
            _try_render("price_panel", dl=dl, csum=csum, default_json_path=default_json_path,
                        debug_label="price_panel")

    # Positions table (either module name)
    if show_positions_table:
        if not _try_render("positions_panel", dl=dl, csum=csum, default_json_path=default_json_path,
                           debug_label="positions_panel"):
            _try_render("positions_table", dl=dl, csum=csum, default_json_path=default_json_path,
                        debug_label="positions_table")

    # Totals under the table
    if show_positions_totals:
        _try_render("positions_totals", dl=dl, csum=csum, default_json_path=default_json_path,
                    debug_label="positions_totals")

    if show_wallets_panel:
        _try_render("wallets_panel", dl=dl, csum=csum, default_json_path=default_json_path,
                    debug_label="wallets_panel")


# convenience pass-throughs (optional)
def render_xcom_check_panel(*, dl: Any, csum: Mapping[str, Any] | None = None,
                            default_json_path: str | None = None, **_: Any) -> None:
    _try_render("xcom_check_panel", dl=dl, csum=csum, default_json_path=default_json_path,
                debug_label="xcom_check_panel")


def render_monitors_summary(*, dl: Any, csum: Mapping[str, Any] | None = None,
                            default_json_path: str | None = None, **_: Any) -> None:
    _try_render("monitors_summary", dl=dl, csum=csum, default_json_path=default_json_path,
                debug_label="monitors_summary")


def render_positions_totals(*, dl: Any, csum: Mapping[str, Any] | None = None,
                            default_json_path: str | None = None, **_: Any) -> None:
    _try_render("positions_totals", dl=dl, csum=csum, default_json_path=default_json_path,
                debug_label="positions_totals")


def render_wallets_panel(*, dl: Any, csum: Mapping[str, Any] | None = None,
                         default_json_path: str | None = None, **_: Any) -> None:
    _try_render("wallets_panel", dl=dl, csum=csum, default_json_path=default_json_path,
                debug_label="wallets_panel")
