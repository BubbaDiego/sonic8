import threading
import sqlite3
from backend.data.data_locker import DataLocker


def test_thread_safe_access(tmp_path):
    db_path = tmp_path / "thr.db"
    dl = DataLocker(str(db_path))
    cur = dl.db.get_cursor()
    cur.execute("CREATE TABLE items (num INTEGER)")
    dl.db.commit()

    errors = []

    def worker(n):
        try:
            with dl.db._lock:
                c = dl.db.get_cursor()
                c.execute("INSERT INTO items (num) VALUES (?)", (n,))
                dl.db.commit()
        except Exception as e:  # pragma: no cover - threads may raise
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not any(isinstance(e, sqlite3.InterfaceError) for e in errors)
    c = dl.db.get_cursor()
    c.execute("SELECT COUNT(*) FROM items")
    assert c.fetchone()[0] == 5
    dl.close()
