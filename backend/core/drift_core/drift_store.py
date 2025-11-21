from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List

from backend.data.data_locker import DataLocker

logger = logging.getLogger(__name__)


class DriftStore:
    """
    Data access layer for Drift-derived data.

    This class is responsible for mapping raw Drift markets and positions
    into Sonic's existing persistence model using DataLocker.

    The initial implementation is stubbed out and will be wired to the
    concrete DataLocker APIs in a follow-up pass.
    """

    def __init__(self, dl: DataLocker) -> None:
        self._dl = dl

    def upsert_positions(self, owner: str, positions: Iterable[Dict[str, Any]]) -> None:
        """
        Persist (or update) the given positions for the specified owner.

        For now this method is a stub; it will be wired to DataLocker in
        a follow-up pass.
        """
        positions_list = list(positions)
        logger.debug(
            "DriftStore.upsert_positions(owner=%s, count=%d)",
            owner,
            len(positions_list),
        )
        # TODO: implement actual DataLocker writes for positions.
        raise NotImplementedError("DriftStore.upsert_positions is not implemented yet.")

    def clear_positions_for_owner(self, owner: str) -> None:
        """
        Remove any existing Drift-derived positions for a given owner.
        """
        logger.debug("DriftStore.clear_positions_for_owner(owner=%s)", owner)
        # TODO: implement delete behavior via DataLocker.
        raise NotImplementedError(
            "DriftStore.clear_positions_for_owner is not implemented yet."
        )

    def get_positions_for_owner(self, owner: str) -> List[Dict[str, Any]]:
        """
        Return current Drift-derived positions for a given owner as plain dicts.
        """
        logger.debug("DriftStore.get_positions_for_owner(owner=%s)", owner)
        # TODO: implement read behavior via DataLocker.
        raise NotImplementedError(
            "DriftStore.get_positions_for_owner is not implemented yet."
        )
