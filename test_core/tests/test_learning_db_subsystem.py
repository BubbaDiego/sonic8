import importlib

def test_basic_logging(tmp_path, monkeypatch):
    db_path = tmp_path / "learning.db"
    monkeypatch.setenv("LEARNING_DB_PATH", str(db_path))
    import learning_database.learning_event_logger as logger
    importlib.reload(logger)
    payload = {"position_id": "p1", "trader_name": "t", "state": "ENRICH"}
    logger.log_learning_event("position_events", payload)
    logger.log_learning_event("position_events", payload)
    dl = logger.LearningDataLocker.get_instance()
    rows = dl.db.fetch_all("position_events")
    assert len(rows) == 1
    assert rows[0]["position_id"] == "p1"
    assert rows[0]["state"] == "ENRICH"
    dl.db.close()
