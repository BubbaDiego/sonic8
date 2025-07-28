"""Central factory for obtaining the shared :class:`DataLocker` instance."""

from backend.core.core_constants import MOTHER_DB_PATH


def get_locker(db_path: str | None = None):
    """Return the singleton :class:`DataLocker` for ``db_path`` or the default."""
    from backend.data.data_locker import DataLocker

    return DataLocker.get_instance(str(db_path or MOTHER_DB_PATH))


__all__ = ["get_locker"]
