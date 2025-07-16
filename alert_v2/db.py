
"""Database helpers for Alert v2"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

_engine = create_engine("sqlite:///alert_v2.db", echo=False, future=True)
SessionLocal = scoped_session(sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True))

def get_session():
    """Return a SQLAlchemy Session (scoped)."""
    return SessionLocal()
