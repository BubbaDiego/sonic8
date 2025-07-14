import pytest
from backend.data.dl_session import DLSessionManager

CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        session_start_time TEXT,
        session_start_value REAL,
        session_goal_value REAL,
        current_session_value REAL,
        session_performance_value REAL,
        status TEXT DEFAULT 'OPEN',
        notes TEXT,
        last_modified TEXT DEFAULT CURRENT_TIMESTAMP
    )
"""

@pytest.fixture()
def session_mgr(dl_tmp):
    cursor = dl_tmp.db.get_cursor()
    cursor.execute(CREATE_TABLE_SQL)
    dl_tmp.db.commit()
    return DLSessionManager(dl_tmp.db)

def test_session_crud_flow(session_mgr):
    s1 = session_mgr.start_session(start_value=10.0, goal_value=20.0, notes="A")
    assert s1.status == "OPEN"
    assert session_mgr.get_active_session().id == s1.id

    updated = session_mgr.update_session(s1.id, {"notes": "B", "current_session_value": 5.0})
    assert updated.notes == "B"
    assert updated.current_session_value == 5.0

    s2 = session_mgr.start_session(start_value=30.0, goal_value=40.0, notes="C")
    assert session_mgr.get_active_session().id == s2.id
    assert session_mgr.get_session_by_id(s1.id).status == "CLOSED"

    sessions = session_mgr.list_sessions()
    assert len(sessions) == 2
    assert sessions[0].id == s2.id

def test_single_open_session_enforced(session_mgr):
    first = session_mgr.start_session()
    second = session_mgr.start_session()
    third = session_mgr.start_session()
    cur = session_mgr.db.get_cursor()
    cur.execute("SELECT COUNT(*) FROM sessions WHERE status='OPEN'")
    count = cur.fetchone()[0]
    assert count == 1
    assert session_mgr.get_active_session().id == third.id

    assert session_mgr.get_session_by_id(first.id).status == "CLOSED"
    assert session_mgr.get_session_by_id(second.id).status == "CLOSED"

def test_reset_and_close_session(session_mgr):
    sess = session_mgr.start_session(start_value=5.0, goal_value=10.0)
    session_mgr.update_session(sess.id, {
        "current_session_value": 7.0,
        "session_performance_value": 8.0
    })
    before = session_mgr.get_active_session().session_start_time

    reset = session_mgr.reset_session()
    assert reset.id == sess.id
    assert reset.current_session_value == 0.0
    assert reset.session_performance_value == 0.0
    assert reset.session_start_value == 0.0
    assert reset.status == "OPEN"
    assert reset.session_start_time != before

    closed = session_mgr.close_session()
    assert closed.status == "CLOSED"
    assert session_mgr.get_active_session() is None

    assert session_mgr.reset_session() is None
    assert session_mgr.close_session() is None
