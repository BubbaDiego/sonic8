from datetime import datetime
from fastapi import APIRouter, Depends
from backend.alert_v2 import AlertRepo

router = APIRouter()

def get_repo():
    return AlertRepo()

@router.get("/alerts")
def list_alerts(repo: AlertRepo = Depends(get_repo)):
    return repo.active_states()

@router.get("/alerts/{alert_id}/events")
def alert_events(alert_id: str, repo: AlertRepo = Depends(get_repo)):
    return repo.last_events(alert_id=alert_id, limit=200)

@router.post("/alerts/{alert_id}/ack")
def ack(alert_id: str, until: datetime, repo: AlertRepo = Depends(get_repo)):
    st = repo.get_state(alert_id)
    st.snoozed_until = until
    repo.save_state(st)
    return {"status": "acknowledged", "until": until}
