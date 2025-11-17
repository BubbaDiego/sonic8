from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.data.data_locker import DataLocker
from backend.models.session import Session, SessionCreate, SessionUpdate

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def get_app_locker() -> DataLocker:
    return DataLocker.get_instance()


@router.get("/", response_model=List[Session])
def list_sessions(
    limit: Optional[int] = Query(default=None, ge=1, le=500),
    dl: DataLocker = Depends(get_app_locker),
) -> List[Session]:
    sessions = dl.session.list_sessions(limit=limit)
    return sessions


@router.get("/active", response_model=Session | None)
def get_active_session(
    dl: DataLocker = Depends(get_app_locker),
) -> Session | None:
    return dl.session.get_active_session()


@router.post("/", response_model=Session)
def start_session(
    payload: SessionCreate,
    dl: DataLocker = Depends(get_app_locker),
) -> Session:
    """Start a new session, closing any existing open one."""

    return dl.session.start_session(
        start_value=payload.session_start_value,
        goal_value=payload.session_goal_value,
        notes=payload.notes,
        session_label=payload.session_label,
        goal_mode=payload.goal_mode,
    )


@router.patch("/{session_id}", response_model=Session)
def update_session(
    session_id: str,
    patch: SessionUpdate,
    dl: DataLocker = Depends(get_app_locker),
) -> Session:
    fields = {k: v for k, v in patch.model_dump(exclude_unset=True).items()}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    return dl.session.update_session(session_id, fields)


@router.post("/close", response_model=Session | None)
def close_session(
    dl: DataLocker = Depends(get_app_locker),
) -> Session | None:
    return dl.session.close_session()
