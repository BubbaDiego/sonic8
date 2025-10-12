from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional


@dataclass
class SummaryCache:
    prices_top3: List[Tuple[str, float]] = field(default_factory=list)
    prices_updated_at: Optional[str] = None
    price_ages: Dict[str, int] = field(default_factory=dict)
    positions_icon_line: Optional[str] = None
    positions_updated_at: Optional[str] = None
    hedge_groups: int = 0
    reasons: Dict[str, str] = field(default_factory=dict)  # 'prices','positions'


_CACHE = SummaryCache()


def set_prices(
    top3: List[Tuple[str, float]],
    updated_iso: Optional[str],
    fresh: Optional[bool] = None,
) -> None:
    if fresh is None:
        if updated_iso:
            prev = _CACHE.prices_updated_at
            fresh = prev is None or updated_iso != prev
        else:
            fresh = False
    # update ages: new data → 0, others +1
    for k in list(_CACHE.price_ages.keys()):
        _CACHE.price_ages[k] = _CACHE.price_ages.get(k, 0) + 1
    for s, _ in top3:
        _CACHE.price_ages[s] = 0 if fresh else _CACHE.price_ages.get(s, 0)
    _CACHE.prices_top3 = top3 or _CACHE.prices_top3
    _CACHE.prices_updated_at = updated_iso or _CACHE.prices_updated_at
    if fresh:
        _CACHE.reasons["prices"] = "fresh"


def set_prices_reason(reason: str) -> None:
    _CACHE.reasons["prices"] = reason


def set_positions_icon_line(
    line: Optional[str], updated_iso: Optional[str], reason: Optional[str] = None
) -> None:
    if line:
        _CACHE.positions_icon_line = line
    if updated_iso:
        _CACHE.positions_updated_at = updated_iso
    if reason:
        _CACHE.reasons["positions"] = reason


def set_hedges(n: int) -> None:
    if n is not None:
        _CACHE.hedge_groups = int(n)


def snapshot_into(summary: Dict) -> Dict:
    """Merge cached values into a summary dict (without overwriting non-empty)."""
    # prices
    summary.setdefault("prices_top3", _CACHE.prices_top3)
    summary.setdefault("prices_updated_at", _CACHE.prices_updated_at)
    summary.setdefault("price_ages", _CACHE.price_ages)
    # positions
    if _CACHE.positions_icon_line and not summary.get("positions_icon_line"):
        summary["positions_icon_line"] = _CACHE.positions_icon_line
    summary.setdefault("positions_updated_at", _CACHE.positions_updated_at)
    # hedges
    summary.setdefault("hedge_groups", _CACHE.hedge_groups)
    # reasons
    if "prices_reason" not in summary and "prices" in _CACHE.reasons:
        summary["prices_reason"] = _CACHE.reasons["prices"]
    if "positions_reason" not in summary and "positions" in _CACHE.reasons:
        summary["positions_reason"] = _CACHE.reasons["positions"]
    return summary
