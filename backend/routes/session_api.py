from fastapi import APIRouter, Depends
from backend.data.data_locker import DataLocker
from backend.deps import get_app_locker
from backend.models.session import Session, SessionCreate, SessionUpdate

router = APIRouter(prefix="/session", tags=["session"])

@router.get("/", response_model=Session | None)
def get_active_session(dl: DataLocker = Depends(get_app_locker)):
    return dl.session.get_active_session()

@router.get("/history", response_model=list[Session])
def list_sessions(limit: int | None = None, dl: DataLocker = Depends(get_app_locker)):
    return dl.session.list_sessions(limit)

@router.post("/", response_model=Session, status_code=201)
def start_session(payload: SessionCreate, dl: DataLocker = Depends(get_app_locker)):
    return dl.session.start_session(
        start_value=payload.session_start_value,
        goal_value=payload.session_goal_value,
        notes=payload.notes,
    )

@router.put("/{sid}", response_model=Session | None)
def update_session(sid: str, payload: SessionUpdate, dl: DataLocker = Depends(get_app_locker)):
    return dl.session.update_session(sid, payload)

@router.put("/", response_model=Session | None)
def update_active_session(payload: SessionUpdate, dl: DataLocker = Depends(get_app_locker)):
    return dl.session.update_session(None, payload)

@router.post("/reset", response_model=Session | None)
def reset_session(dl: DataLocker = Depends(get_app_locker)):
    return dl.session.reset_session()

@router.post("/close", response_model=Session | None)
def close_session(dl: DataLocker = Depends(get_app_locker)):
    return dl.session.close_session()

__all__ = ["router"]
