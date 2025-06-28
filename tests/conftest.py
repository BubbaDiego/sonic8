import pytest, tempfile, os
from data.data_locker import DataLocker

@pytest.fixture(scope="function")
def dl_tmp():
    tmp_db = tempfile.NamedTemporaryFile(delete=False).name
    dl = DataLocker(tmp_db)
    yield dl
    dl.close()
    os.remove(tmp_db)
