
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from alert_v2.models import Base
from alert_v2.repository import AlertRepo

@pytest.fixture(scope="session")
def engine():
    eng = create_engine("sqlite+pysqlite:///:memory:", echo=False, future=True)
    Base.metadata.create_all(bind=eng)
    return eng

@pytest.fixture(scope="function")
def session(engine):
    connection = engine.connect()
    txn = connection.begin()
    Session = sessionmaker(bind=connection, autoflush=False, autocommit=False, future=True)
    session = Session()

    yield session

    session.close()
    txn.rollback()
    connection.close()

@pytest.fixture(scope="function")
def repo(session):
    return AlertRepo(session=session)
