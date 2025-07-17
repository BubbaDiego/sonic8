
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

_engine = create_engine("sqlite:///alert_v2_hybrid.db", echo=False, future=True)
SessionLocal = scoped_session(sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True))

def get_session():
    return SessionLocal()
