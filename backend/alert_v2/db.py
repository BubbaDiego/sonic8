
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from backend.core.core_constants import MOTHER_DB_PATH

_engine = create_engine(f"sqlite:///{MOTHER_DB_PATH}", echo=False, future=True)
SessionLocal = scoped_session(sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True))

def get_session():
    return SessionLocal()
