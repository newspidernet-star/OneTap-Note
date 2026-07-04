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
    _auto_migrate()


def _auto_migrate() -> None:
    """轻量自动迁移：给已有表补新列（SQLAlchemy create_all 不改旧表）。
    仅做加列，不删不改类型，适合开发期 schema 演进。
    """
    from sqlalchemy import text, inspect
    insp = inspect(engine)
    # sessions 表补 client_id / last_seen_at
    if "sessions" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("sessions")}
        with engine.begin() as conn:
            if "client_id" not in cols:
                conn.execute(text("ALTER TABLE sessions ADD COLUMN client_id VARCHAR(64)"))
            if "last_seen_at" not in cols:
                conn.execute(text("ALTER TABLE sessions ADD COLUMN last_seen_at VARCHAR(50)"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()