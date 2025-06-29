from core.locker_factory import get_locker
from core.logging import log
from .infrastructure.stores import AlertStore, _DBAdapter

class AlertController:
    """High level operations for managing alerts."""

    def __init__(self, data_locker=None):
        self.dl = data_locker or get_locker()
        db_adapter = _DBAdapter(str(self.dl.db.db_path))
        self.store = AlertStore(db_adapter)

    def delete_alert(self, alert_id: str) -> bool:
        """Delete an alert by id using the underlying AlertStore."""
        return self.store.delete_alert(alert_id)

__all__ = ["AlertController"]
