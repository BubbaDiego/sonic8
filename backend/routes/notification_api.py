"""APIRouter exposing notification endpoints for React header dropdown."""

from fastapi import APIRouter, Depends
from backend.data.data_locker import DataLocker  # type: ignore
from backend.core.xcom_core.notification_service import NotificationService  # type: ignore
from backend.deps import get_app_locker

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/")
def list_notifications(status: str = "all", dl: DataLocker = Depends(get_app_locker)):
    svc = NotificationService(dl.db)
    return svc.list(status=status)


@router.get("/unread-count")
def unread_count(dl: DataLocker = Depends(get_app_locker)):
    svc = NotificationService(dl.db)
    return {"count": svc.unread_count()}


@router.post("/{notif_id}/read")
def mark_read(notif_id: str, dl: DataLocker = Depends(get_app_locker)):
    svc = NotificationService(dl.db)
    svc.mark_read(notif_id)
    return {"success": True}


@router.post("/mark_all_read")
def mark_all_read(dl: DataLocker = Depends(get_app_locker)):
    svc = NotificationService(dl.db)
    svc.mark_all_read()
    return {"success": True}


