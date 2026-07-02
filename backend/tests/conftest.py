import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import base, __init__ as _models  # noqa: F401
from app.database import get_db
from app.main import create_app


@pytest.fixture
async def client():
    app = create_app()

    # Override get_db with in-memory SQLite
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    base.Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
    test_engine.dispose()


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    base.Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def db(db_session):
    return db_session
