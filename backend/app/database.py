from collections.abc import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models.base import Base


def get_engine():
    settings = get_settings()
    return create_engine(settings.db_url, connect_args={"check_same_thread": False})


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
session_factory = SessionLocal


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def init_db():
    from app.models import __init__  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()